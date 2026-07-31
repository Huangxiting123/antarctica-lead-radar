from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

from .http import ConnectorError, request_json


class RedditConnector:
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    API_URL = "https://oauth.reddit.com"

    def get_app_token(self, client_id: str, client_secret: str, user_agent: str) -> str:
        credentials = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()
        body = urllib.parse.urlencode({"grant_type": "client_credentials"}).encode()
        request = urllib.request.Request(
            self.TOKEN_URL,
            data=body,
            headers={"Authorization": f"Basic {credentials}", "User-Agent": user_agent, "Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise ConnectorError(f"Reddit OAuth 失败：{exc}") from exc
        token = str(payload.get("access_token") or "")
        if not token:
            raise ConnectorError(str(payload.get("error") or "Reddit 未返回 access_token"))
        return token

    def search_comments(
        self,
        client_id: str,
        client_secret: str,
        user_agent: str,
        keyword: str,
        subreddit: str = "",
        max_posts: int = 20,
        max_comments_per_post: int = 200,
    ) -> list[dict[str, Any]]:
        token = self.get_app_token(client_id.strip(), client_secret.strip(), user_agent.strip())
        headers = {"Authorization": f"Bearer {token}", "User-Agent": user_agent.strip()}
        endpoint = f"{self.API_URL}/r/{subreddit.strip()}/search" if subreddit.strip() else f"{self.API_URL}/search"
        search = request_json(endpoint, query={"q": keyword, "restrict_sr": "1" if subreddit.strip() else "0", "sort": "relevance", "type": "link", "limit": min(100, max_posts), "raw_json": 1}, headers=headers)
        posts = ((search.get("data") or {}).get("children") or [])[:max(1, min(max_posts, 100))]
        records: list[dict[str, Any]] = []
        for wrapped in posts:
            post = wrapped.get("data") or {}
            post_id = str(post.get("id") or "")
            if not post_id:
                continue
            payload = request_json(f"{self.API_URL}/comments/{post_id}", query={"limit": min(500, max_comments_per_post), "depth": 10, "raw_json": 1}, headers=headers)
            if not isinstance(payload, list) or len(payload) < 2:
                continue
            comments = ((payload[1].get("data") or {}).get("children") or [])
            flat: list[dict[str, Any]] = []
            self._flatten_comments(comments, flat, max_comments_per_post)
            permalink = str(post.get("permalink") or "")
            for comment in flat:
                comment_id = str(comment.get("id") or "")
                records.append({
                    "platform": "Reddit",
                    "user_name": str(comment.get("author") or "[deleted]"),
                    "user_id": str(comment.get("author_fullname") or comment.get("author") or ""),
                    "content": str(comment.get("body") or ""),
                    "comment_time": str(comment.get("created_utc") or ""),
                    "video_id": post_id,
                    "video_title": str(post.get("title") or ""),
                    "video_url": "https://www.reddit.com" + permalink + comment_id,
                    "platform_comment_id": comment_id,
                })
        return records

    def _flatten_comments(self, children: list[dict[str, Any]], output: list[dict[str, Any]], limit: int) -> None:
        for wrapped in children:
            if len(output) >= limit:
                return
            if wrapped.get("kind") != "t1":
                continue
            data = wrapped.get("data") or {}
            output.append(data)
            replies = data.get("replies")
            if isinstance(replies, dict):
                nested = ((replies.get("data") or {}).get("children") or [])
                self._flatten_comments(nested, output, limit)
