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

class API:
    def __init__(self):
        load_dotenv(verbose=True)
        self.API_KEY = os.getenv('API_KEY')     # 你的 API 金鑰

    def get_comments(self, url: str, page_size: int = 100, pages: int = 5, min_likes: int = 1, order: str = "relevance") -> list:
        VIDEO_ID = self.extract_video_id(url)
        if not VIDEO_ID:
            return []  # 或 raise ValueError("Invalid YouTube URL")

        page_size = max(1, min(100, int(page_size)))

        http = httplib2.Http(timeout=10)
        youtube = build("youtube", "v3", developerKey=self.API_KEY, http=http)

        comments = []
        next_page_token = None

        for page_count in range(1, pages + 1):
            try:
                response = (
                    youtube.commentThreads()
                        .list(
                            part="snippet",
                            videoId=VIDEO_ID,
                            maxResults=page_size,
                            order=order,
                            pageToken=next_page_token,
                            textFormat="plainText"
                        )
                        .execute()
                )
            except Exception as e:
                print(f"抓取失敗：{e}")
                break

            for item in response.get("items", []):
                top = item["snippet"]["topLevelComment"]
                s = top["snippet"]
                likes = s.get("likeCount", 0)

                if likes >= min_likes:
                    comments.append({
                        "原留言": s.get("textDisplay", ""),
                        "按讚數": likes,
                        "回覆數": item["snippet"].get("totalReplyCount", 0),
                        "留言時間": s.get("publishedAt", None),
                    })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

        return comments

    
    def extract_video_id(self, url: str) -> str:
        parsed_url = urlparse(url)

        # 處理 youtu.be 短網址
        if parsed_url.netloc == "youtu.be":
            return parsed_url.path.strip("/")

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
            part="snippet",
            id=video_id
        ).execute()

        items = resp.get("items", [])
        if not items:
            return None

        snippet = items[0]["snippet"]
        return {
            "title": snippet.get("title"),
            "channel": snippet.get("channelTitle"),
            "published_at": snippet.get("publishedAt"),
        }
