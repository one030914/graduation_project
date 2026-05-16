from __future__ import annotations

import pandas as pd

from data.youtube.api import API
from data.preprocess.pipeline import batch_preprocess_comments
from configs.schema import CommentDataset

def collect_comments(
    url: str,
    *,
    pages: int = 5,
    page_size: int = 100,
    min_likes: int = 0,
    order: str = "relevance",
) -> CommentDataset:
    api = API()

    video_id = api.extract_video_id(url)
    if not video_id:
        return CommentDataset(
            video_id="",
            title="",
            url=url,
            df=pd.DataFrame(),
            error="Invalid YouTube URL / video_id not found.",
        )

    info = api.get_video_info(video_id)
    title = (info or {}).get("title") or video_id

    comments = api.get_comments(
        url=url,
        page_size=page_size,
        pages=pages,
        min_likes=min_likes,
        order=order,
    )

    if not comments:
        return CommentDataset(
            video_id=video_id,
            title=title,
            url=url,
            df=pd.DataFrame(),
            error="No comments found.",
        )

    df = batch_preprocess_comments(comments)

    if df.empty:
        return CommentDataset(
            video_id=video_id,
            title=title,
            url=url,
            df=df,
            error="No valid comments after preprocessing.",
        )

    return CommentDataset(
        video_id=video_id,
        title=title,
        url=url,
        df=df,
        error=None,
    )