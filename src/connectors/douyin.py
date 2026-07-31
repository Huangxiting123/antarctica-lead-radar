from __future__ import annotations

from datetime import datetime
from typing import Any

from .http import ConnectorError, request_json


class DouyinConnector:
    """Official Douyin Open Platform connector for an authorized account."""

    BASE_URL = "https://open.douyin.com"

    @staticmethod
    def _check(payload: dict[str, Any]) -> dict[str, Any]:
        data = payload.get("data") or {}
        extra = payload.get("extra") or {}
        code = data.get("error_code", extra.get("error_code", 0))
        if code not in (0, "0", None):
            description = data.get("description") or extra.get("description") or "抖音接口返回错误"
            raise ConnectorError(f"抖音错误 {code}: {description}")
        return data

    def list_authorized_videos(
        self,
        access_token: str,
        open_id: str,
        max_pages: int = 5,
    ) -> list[dict[str, Any]]:
        videos: list[dict[str, Any]] = []
        cursor = 0
        for _ in range(max(1, min(max_pages, 20))):
            payload = request_json(
                self.BASE_URL + "/video/list/",
                query={"open_id": open_id, "cursor": cursor, "count": 20},
                headers={"access-token": access_token},
            )
            data = self._check(payload)
            for video in data.get("list") or []:
                videos.append(
                    {
                        "video_id": str(video.get("item_id") or video.get("video_id") or ""),
                        "title": str(video.get("title") or ""),
                        "url": str(video.get("share_url") or ""),
                        "create_time": video.get("create_time"),
                        "comment_count": (video.get("statistics") or {}).get("comment_count", 0),
                    }
                )
            if not data.get("has_more"):
                break
            cursor = int(data.get("cursor") or 0)
        return videos

    def list_comments(
        self,
        access_token: str,
        open_id: str,
        item_id: str,
        video_title: str = "",
        video_url: str = "",
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        comments: list[dict[str, Any]] = []
        cursor = 0
        for _ in range(max(1, min(max_pages, 50))):
            payload = request_json(
                self.BASE_URL + "/video/comment/list/",
                query={"open_id": open_id, "item_id": item_id, "cursor": cursor, "count": 50},
                headers={"access-token": access_token},
            )
            data = self._check(payload)
            for comment in data.get("list") or []:
                create_time = comment.get("create_time")
                if isinstance(create_time, (int, float)):
                    create_time = datetime.fromtimestamp(create_time).astimezone().isoformat(timespec="seconds")
                user = comment.get("user") or {}
                comments.append(
                    {
                        "platform": "抖音",
                        "user_name": str(user.get("nickname") or comment.get("nickname") or ""),
                        "user_id": str(user.get("open_id") or comment.get("open_id") or ""),
                        "content": str(comment.get("comment_text") or comment.get("text") or ""),
                        "comment_time": str(create_time or ""),
                        "video_id": item_id,
                        "video_title": video_title,
                        "video_url": video_url,
                        "platform_comment_id": str(comment.get("comment_id") or comment.get("id") or ""),
                    }
                )
            if not data.get("has_more"):
                break
            cursor = int(data.get("cursor") or 0)
        return comments

    def reply_comment(
        self,
        access_token: str,
        open_id: str,
        item_id: str,
        comment_id: str,
        content: str,
    ) -> dict[str, Any]:
        if not content.strip():
            raise ValueError("回复内容不能为空")
        payload = request_json(
            self.BASE_URL + "/video/comment/reply/",
            query={"open_id": open_id},
            data={"item_id": item_id, "comment_id": comment_id, "content": content.strip()},
            headers={"access-token": access_token},
        )
        self._check(payload)
        return payload
