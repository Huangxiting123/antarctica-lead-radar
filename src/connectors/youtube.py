from __future__ import annotations

from typing import Any

from .http import ConnectorError, request_json


class YouTubeConnector:
    BASE_URL = "https://www.googleapis.com/youtube/v3"

    @staticmethod
    def _check(payload: dict[str, Any]) -> None:
        if "error" in payload:
            error = payload["error"]
            raise ConnectorError(str(error.get("message") or error))

    def search_videos(
        self,
        api_key: str,
        keyword: str,
        max_videos: int = 25,
        language: str = "zh-Hans",
    ) -> list[dict[str, Any]]:
        max_videos = max(1, min(max_videos, 100))
        videos: list[dict[str, Any]] = []
        page_token = ""
        while len(videos) < max_videos:
            query = {
                "key": api_key,
                "part": "snippet",
                "type": "video",
                "q": keyword,
                "maxResults": min(50, max_videos - len(videos)),
                "order": "relevance",
                "relevanceLanguage": language,
                "safeSearch": "moderate",
            }
            if page_token:
                query["pageToken"] = page_token
            payload = request_json(self.BASE_URL + "/search", query=query)
            self._check(payload)
            for item in payload.get("items") or []:
                video_id = str((item.get("id") or {}).get("videoId") or "")
                snippet = item.get("snippet") or {}
                if video_id:
                    videos.append(
                        {
                            "video_id": video_id,
                            "title": str(snippet.get("title") or ""),
                            "url": f"https://www.youtube.com/watch?v={video_id}",
                            "channel_title": str(snippet.get("channelTitle") or ""),
                            "published_at": str(snippet.get("publishedAt") or ""),
                        }
                    )
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token:
                break
        return videos[:max_videos]

    def list_comments(
        self,
        api_key: str,
        video: dict[str, Any],
        max_comments: int = 500,
    ) -> list[dict[str, Any]]:
        max_comments = max(1, min(max_comments, 5000))
        comments: list[dict[str, Any]] = []
        page_token = ""
        while len(comments) < max_comments:
            query = {
                "key": api_key,
                "part": "snippet",
                "videoId": video["video_id"],
                "maxResults": min(100, max_comments - len(comments)),
                "order": "time",
                "textFormat": "plainText",
            }
            if page_token:
                query["pageToken"] = page_token
            payload = request_json(self.BASE_URL + "/commentThreads", query=query)
            self._check(payload)
            for item in payload.get("items") or []:
                top = ((item.get("snippet") or {}).get("topLevelComment") or {})
                snippet = top.get("snippet") or {}
                comments.append(
                    {
                        "platform": "YouTube",
                        "user_name": str(snippet.get("authorDisplayName") or ""),
                        "user_id": str((snippet.get("authorChannelId") or {}).get("value") or ""),
                        "content": str(snippet.get("textDisplay") or ""),
                        "comment_time": str(snippet.get("publishedAt") or ""),
                        "video_id": video["video_id"],
                        "video_title": str(video.get("title") or ""),
                        "video_url": str(video.get("url") or ""),
                        "platform_comment_id": str(top.get("id") or item.get("id") or ""),
                    }
                )
            page_token = str(payload.get("nextPageToken") or "")
            if not page_token:
                break
        return comments[:max_comments]
