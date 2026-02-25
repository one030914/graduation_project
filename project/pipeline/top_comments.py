from __future__ import annotations

from typing import List

from data.youtube.api import API
from pipeline.schema import TopCommentsResult, TopComment, Order, SortBy

def get_top_comments(
    url: str,
    *,
    n: int = 10,
    pages: int = 5,
    page_size: int = 100,
    min_likes: int = 1,
    order: Order = "relevance",
    sort_by: SortBy = "likes",
) -> TopCommentsResult:
    api = API()
    
    video_id = api.extract_video_id(url)
    if not video_id:
        return TopCommentsResult(error="Invalid YouTube URL / video_id not found.")

    video_info = api.get_video_info(video_id)
    title = (video_info or {}).get("title") or video_id
    
    comments = api.get_comments(
        url=url,
        page_size=page_size,
        pages=pages,
        min_likes=min_likes,
        order=order,
    )

    def _to_int(x) -> int:
        try:
            return int(x)
        except Exception:
            return 0

    items: List[TopComment] = []
    for c in comments:
        text = str(c.get("原留言", "")).strip()
        if not text:
            continue
        items.append(
            TopComment(
                text=text,
                like_count=_to_int(c.get("按讚數", 0)),
                reply_count=_to_int(c.get("回覆數", 0)),
                published_at=c.get("留言時間"),
                author=c.get("author"),
                comment_id=c.get("comment_id"),
            )
        )

    if sort_by == "replies":
        items.sort(key=lambda x: x.reply_count, reverse=True)
    elif sort_by == "time":
        items.sort(key=lambda x: (x.published_at or ""), reverse=True)
    else:
        items.sort(key=lambda x: x.like_count, reverse=True)

    # limit the number of comments
    n = max(1, min(int(n), 10))
    top = items[:n]

    return TopCommentsResult(
        video_id=video_id,
        title=title,
        url=url,
        top=top,
        total_fetched=len(items),
        order=order,
        sort_by=sort_by,
    )