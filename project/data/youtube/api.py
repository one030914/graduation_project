"""
Get Youtube comments from API
"""

import httplib2
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pandas as pd
import socket
from pathlib import Path
import re
from urllib.parse import urlparse, parse_qs
import os
from dotenv import load_dotenv

ISO_8601_DURATION_RE = re.compile(
    r"^P(?:(?P<days>\d+)D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?$"
)


def parse_youtube_duration_seconds(value: str | None) -> int | None:
    if not value:
        return None

    match = ISO_8601_DURATION_RE.match(str(value).strip())
    if not match:
        return None

    parts = {key: int(raw) if raw else 0 for key, raw in match.groupdict().items()}
    if not any(parts.values()):
        return 0 if str(value).strip() == "PT0S" else None

    return (
        parts["days"] * 86400
        + parts["hours"] * 3600
        + parts["minutes"] * 60
        + parts["seconds"]
    )


class API:
    def __init__(self):
        load_dotenv(verbose=True)
        self.API_KEY = os.getenv('API_KEY')     # 你的 API 金鑰

    @staticmethod
    def _comment_row(
        comment: dict,
        *,
        thread_id: str,
        parent_comment_id: str | None = None,
        sample_order: str = "relevance",
    ) -> dict:
        snippet = comment.get("snippet") or {}
        is_reply = parent_comment_id is not None
        return {
            "comment_id": comment.get("id"),
            "thread_id": thread_id,
            "parent_comment_id": parent_comment_id,
            "is_reply": is_reply,
            "sample_order": sample_order,
            "author": snippet.get("authorDisplayName"),
            "raw_text": snippet.get("textDisplay", ""),
            "like_count": snippet.get("likeCount", 0),
            "reply_count": 0 if is_reply else None,
            "published_at": snippet.get("publishedAt"),
        }

    def _get_thread_replies(
        self,
        youtube,
        *,
        parent_comment_id: str,
        thread_id: str,
        limit: int,
        sample_order: str,
    ) -> list[dict]:
        if limit <= 0:
            return []

        response = (
            youtube.comments()
                .list(
                    part="snippet",
                    parentId=parent_comment_id,
                    maxResults=min(100, limit),
                    textFormat="plainText",
                )
                .execute()
        )
        return [
            self._comment_row(
                item,
                thread_id=thread_id,
                parent_comment_id=parent_comment_id,
                sample_order=sample_order,
            )
            for item in response.get("items", [])[:limit]
        ]

    def get_comments(
        self,
        url: str,
        page_size: int = 100,
        pages: int = 15,
        min_likes: int = 1,
        order: str = "relevance",
        recent_pages: int = 5,
        include_replies: bool = True,
        max_replies_per_thread: int = 5,
        max_reply_threads: int = 30,
        max_total_replies: int = 300,
    ) -> list:
        VIDEO_ID = self.extract_video_id(url)
        if not VIDEO_ID:
            return []  # 或 raise ValueError("Invalid YouTube URL")

        page_size = max(1, min(100, int(page_size)))
        pages = max(0, int(pages))
        recent_pages = max(0, int(recent_pages))
        max_replies_per_thread = max(0, int(max_replies_per_thread))
        max_reply_threads = max(0, int(max_reply_threads))
        max_total_replies = max(0, int(max_total_replies))

        http = httplib2.Http(timeout=10)
        youtube = build("youtube", "v3", developerKey=self.API_KEY, http=http)

        comments = []
        seen_comment_ids = set()
        processed_reply_threads = set()
        expanded_reply_threads = 0
        total_replies = 0
        sampling_plans = [(order, pages)]
        if order != "time" and recent_pages > 0:
            sampling_plans.append(("time", recent_pages))

        for sample_order, page_limit in sampling_plans:
            next_page_token = None

            for _ in range(page_limit):
                try:
                    response = (
                        youtube.commentThreads()
                            .list(
                                part="snippet,replies" if include_replies else "snippet",
                                videoId=VIDEO_ID,
                                maxResults=page_size,
                                order=sample_order,
                                pageToken=next_page_token,
                                textFormat="plainText"
                            )
                            .execute()
                    )
                except Exception as e:
                    print(f"抓取失敗 ({sample_order})：{e}")
                    break

                for item in response.get("items", []):
                    top = item["snippet"]["topLevelComment"]
                    s = top["snippet"]
                    likes = s.get("likeCount", 0)
                    thread_id = item.get("id") or top.get("id")
                    top_comment_id = top.get("id")

                    if likes >= min_likes and top_comment_id not in seen_comment_ids:
                        row = self._comment_row(
                            top,
                            thread_id=thread_id,
                            sample_order=sample_order,
                        )
                        row["reply_count"] = item["snippet"].get("totalReplyCount", 0)
                        comments.append(row)
                        seen_comment_ids.add(top_comment_id)

                    if (
                        not include_replies
                        or total_replies >= max_total_replies
                        or thread_id in processed_reply_threads
                    ):
                        continue
                    processed_reply_threads.add(thread_id)

                    reply_limit = min(
                        max_replies_per_thread,
                        max_total_replies - total_replies,
                    )
                    embedded_replies = (item.get("replies") or {}).get("comments", [])
                    thread_replies = [
                        self._comment_row(
                            reply,
                            thread_id=thread_id,
                            parent_comment_id=top_comment_id,
                            sample_order=sample_order,
                        )
                        for reply in embedded_replies[:reply_limit]
                    ]

                    total_reply_count = item["snippet"].get("totalReplyCount", 0)
                    should_expand = (
                        total_reply_count > len(thread_replies)
                        and expanded_reply_threads < max_reply_threads
                        and reply_limit > len(thread_replies)
                    )
                    if should_expand:
                        try:
                            thread_replies = self._get_thread_replies(
                                youtube,
                                parent_comment_id=top_comment_id,
                                thread_id=thread_id,
                                limit=reply_limit,
                                sample_order=sample_order,
                            )
                            expanded_reply_threads += 1
                        except Exception as e:
                            print(f"回覆補抓失敗 ({top_comment_id})：{e}")

                    for reply in thread_replies:
                        reply_id = reply.get("comment_id")
                        if reply_id in seen_comment_ids:
                            continue
                        comments.append(reply)
                        seen_comment_ids.add(reply_id)
                        total_replies += 1
                        if total_replies >= max_total_replies:
                            break

                next_page_token = response.get("nextPageToken")
                if not next_page_token:
                    break

        return comments

    
    def extract_video_id(self, url: str) -> str:
        parsed_url = urlparse(url)

        # 處理短網址
        if parsed_url.netloc == "youtu.be":
            return parsed_url.path.strip("/")

        # 處理 Shorts
        if parsed_url.path.startswith("/shorts/"):
            return parsed_url.path.split("/")[2]

        # 處理 youtube.com/watch?v=xxxx
        if parsed_url.path == "/watch":
            query = parse_qs(parsed_url.query)
            return query.get("v", [None])[0]

        # 處理其他可能格式（如嵌入）
        match = re.search(r"(?:v=|\/embed\/|\/v\/|youtu\.be\/)([a-zA-Z0-9_-]{11})", url)
        if match:
            return match.group(1)

        return None
    
    def get_video_info(self, video_id: str) -> dict | None:
        if not video_id:
            return None

        youtube = build("youtube", "v3", developerKey=self.API_KEY)
        resp = youtube.videos().list(
            part="snippet,contentDetails",
            id=video_id
        ).execute()

        items = resp.get("items", [])
        if not items:
            return None

        snippet = items[0]["snippet"]
        content_details = items[0].get("contentDetails") or {}
        return {
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
            "duration_seconds": parse_youtube_duration_seconds(content_details.get("duration")),
        }
