from __future__ import annotations

from typing import Any

from .http import ConnectorError, request_json


class MetaConnector:
    BASE_URL = "https://graph.facebook.com/v26.0"

    @staticmethod
    def _check(payload: dict[str, Any]) -> None:
        if payload.get("error"):
            error = payload["error"]
            raise ConnectorError(str(error.get("message") or error))

    def facebook_page_comments(self, page_token: str, page_id: str, max_posts: int = 20, max_comments: int = 200) -> list[dict[str, Any]]:
        feed = request_json(f"{self.BASE_URL}/{page_id}/feed", query={"fields": "id,message,created_time,permalink_url", "limit": min(100, max_posts), "access_token": page_token})
        self._check(feed)
        records: list[dict[str, Any]] = []
        for post in (feed.get("data") or [])[:max_posts]:
            post_id = str(post.get("id") or "")
            comments = request_json(f"{self.BASE_URL}/{post_id}/comments", query={"fields": "id,message,created_time,from", "limit": min(100, max_comments), "access_token": page_token})
            self._check(comments)
            for item in (comments.get("data") or [])[:max_comments]:
                author = item.get("from") or {}
                records.append({"platform": "Facebook", "user_name": str(author.get("name") or ""), "user_id": str(author.get("id") or ""), "content": str(item.get("message") or ""), "comment_time": str(item.get("created_time") or ""), "video_id": post_id, "video_title": str(post.get("message") or "")[:120], "video_url": str(post.get("permalink_url") or ""), "platform_comment_id": str(item.get("id") or "")})
        return records

    def instagram_comments(self, access_token: str, ig_user_id: str, max_media: int = 20, max_comments: int = 200) -> list[dict[str, Any]]:
        media = request_json(f"{self.BASE_URL}/{ig_user_id}/media", query={"fields": "id,caption,timestamp,permalink", "limit": min(100, max_media), "access_token": access_token})
        self._check(media)
        records: list[dict[str, Any]] = []
        for post in (media.get("data") or [])[:max_media]:
            media_id = str(post.get("id") or "")
            comments = request_json(f"{self.BASE_URL}/{media_id}/comments", query={"fields": "id,text,timestamp,username", "limit": min(100, max_comments), "access_token": access_token})
            self._check(comments)
            for item in (comments.get("data") or [])[:max_comments]:
                username = str(item.get("username") or "")
                records.append({"platform": "Instagram", "user_name": username, "user_id": username, "content": str(item.get("text") or ""), "comment_time": str(item.get("timestamp") or ""), "video_id": media_id, "video_title": str(post.get("caption") or "")[:120], "video_url": str(post.get("permalink") or ""), "platform_comment_id": str(item.get("id") or "")})
        return records
