from __future__ import annotations

from typing import Any

from .http import ConnectorError, request_json


class XConnector:
    BASE_URL = "https://api.x.com/2/tweets/search/recent"

    def search_posts(
        self,
        bearer_token: str,
        keyword: str,
        max_posts: int = 100,
        language: str = "",
        region_code: str = "",
        replies_only: bool = False,
    ) -> list[dict[str, Any]]:
        if not bearer_token.strip() or not keyword.strip():
            raise ValueError("Bearer Token 和关键词不能为空")
        query_text = f"({keyword.strip()})"
        if language:
            query_text += f" lang:{language.split('-')[0]}"
        if region_code:
            query_text += f" place_country:{region_code.upper()}"
        if replies_only:
            query_text += " is:reply"

        max_posts = max(10, min(max_posts, 1000))
        page_token = ""
        records: list[dict[str, Any]] = []
        while len(records) < max_posts:
            query = {
                "query": query_text,
                "max_results": min(100, max_posts - len(records)),
                "tweet.fields": "id,text,author_id,created_at,conversation_id,lang,geo",
                "expansions": "author_id",
                "user.fields": "id,name,username",
            }
            if page_token:
                query["next_token"] = page_token
            payload = request_json(self.BASE_URL, query=query, headers={"Authorization": f"Bearer {bearer_token.strip()}"})
            if payload.get("errors") and not payload.get("data"):
                raise ConnectorError(str(payload["errors"]))
            users = {str(u.get("id")): u for u in (payload.get("includes") or {}).get("users") or []}
            for post in payload.get("data") or []:
                author_id = str(post.get("author_id") or "")
                user = users.get(author_id, {})
                username = str(user.get("username") or "")
                post_id = str(post.get("id") or "")
                records.append({
                    "platform": "X / Twitter",
                    "user_name": str(user.get("name") or username),
                    "user_id": username or author_id,
                    "content": str(post.get("text") or ""),
                    "comment_time": str(post.get("created_at") or ""),
                    "video_id": str(post.get("conversation_id") or post_id),
                    "video_title": f"X 搜索：{keyword}",
                    "video_url": f"https://x.com/{username or 'i'}/status/{post_id}",
                    "platform_comment_id": post_id,
                })
            page_token = str((payload.get("meta") or {}).get("next_token") or "")
            if not page_token:
                break
        return records[:max_posts]
