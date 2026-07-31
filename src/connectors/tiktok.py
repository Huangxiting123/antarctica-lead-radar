from __future__ import annotations

from datetime import datetime
from typing import Any

from .http import ConnectorError, request_json


class TikTokResearchConnector:
    BASE_URL = "https://open.tiktokapis.com/v2/research"

    @staticmethod
    def _check(payload: dict[str, Any]) -> dict[str, Any]:
        error = payload.get("error") or {}
        if error.get("code") not in (None, "", "ok"):
            raise ConnectorError(str(error.get("message") or error))
        return payload.get("data") or {}

    def collect(self, access_token: str, keyword: str, region_codes: list[str], start_date: str, end_date: str, max_videos: int = 20, max_comments: int = 200) -> list[dict[str, Any]]:
        conditions: list[dict[str, Any]] = [{"operation": "EQ", "field_name": "keyword", "field_values": [keyword]}]
        if region_codes:
            conditions.insert(0, {"operation": "IN", "field_name": "region_code", "field_values": region_codes})
        video_payload = request_json(
            self.BASE_URL + "/video/query/",
            query={"fields": "id,video_description,create_time,region_code,username,comment_count"},
            data={"query": {"and": conditions}, "start_date": start_date, "end_date": end_date, "max_count": min(100, max_videos), "cursor": 0},
            headers={"Authorization": f"Bearer {access_token.strip()}"},
        )
        videos = self._check(video_payload).get("videos") or []
        records: list[dict[str, Any]] = []
        for video in videos[:max_videos]:
            video_id = str(video.get("id") or video.get("video_id") or "")
            if not video_id:
                continue
            cursor = 0
            while True:
                comment_payload = request_json(
                    self.BASE_URL + "/video/comment/list/",
                    query={"fields": "id,video_id,text,like_count,reply_count,parent_comment_id,create_time"},
                    data={"video_id": int(video_id), "max_count": min(100, max_comments - len([r for r in records if r.get('video_id') == video_id])), "cursor": cursor},
                    headers={"Authorization": f"Bearer {access_token.strip()}"},
                )
                data = self._check(comment_payload)
                for item in data.get("comments") or []:
                    created = item.get("create_time")
                    if isinstance(created, (int, float)):
                        created = datetime.fromtimestamp(created).astimezone().isoformat(timespec="seconds")
                    records.append({"platform": "TikTok", "user_name": "", "user_id": "", "content": str(item.get("text") or ""), "comment_time": str(created or ""), "video_id": video_id, "video_title": str(video.get("video_description") or ""), "video_url": f"https://www.tiktok.com/@{video.get('username', '')}/video/{video_id}", "platform_comment_id": str(item.get("id") or "")})
                if not data.get("has_more") or len([r for r in records if r.get('video_id') == video_id]) >= max_comments:
                    break
                cursor = int(data.get("cursor") or 0)
        return records
