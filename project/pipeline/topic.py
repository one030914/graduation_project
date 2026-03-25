from __future__ import annotations

from data.youtube.api import API
from data.preprocess.pipeline import batch_preprocess_comments
from pipeline.schema import TopicsResult, TopicCluster
from model.topic.zh import build_topics_zh
from model.topic.en import build_topics_en

def get_main_language(df) -> str:
    counts = df["語言"].value_counts().to_dict()
    zh = counts.get("zh", 0)
    en = counts.get("en", 0)
    unknown = counts.get("unknown", 0)
    return "zh" if zh >= en and zh >= unknown else "en" if en >= zh and en >= unknown else "unknown"

def build_topics(
    url: str,
    *,
    pages: int = 5,
    page_size: int = 100,
    min_likes: int = 1,
) -> TopicsResult:
    api = API()
    video_id = api.extract_video_id(url)
    if not video_id:
        return TopicsResult(url=url, error="Invalid YouTube URL")

    info = api.get_video_info(video_id)
    title = (info or {}).get("title", video_id)

    comments = api.get_comments(
        url=url,
        page_size=page_size,
        pages=pages,
        min_likes=min_likes,
        order="relevance"
    )

    if not comments:
        return TopicsResult(url=url, title=title, error="No comments found")

    df = batch_preprocess_comments(comments)
    if df.empty:
        return TopicsResult(url=url, title=title, error="No valid comments after preprocessing")

    main_lang = get_main_language(df)
    df_lang = df[df["語言"] == main_lang].copy()

    if df_lang.empty:
        return TopicsResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            topics=[]
        )
        
    if len(df_lang) < 15:
        return TopicsResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            topics=[],
            error="留言數不足以形成穩定主題群"
        )

    if main_lang == "zh":
        topics = build_topics_zh(df_lang)
    elif main_lang == "en":
        topics = build_topics_en(df_lang)
    else:
        return TopicsResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            topics=[],
            error="無法分析此語言"
        )

    return TopicsResult(
        url=url,
        title=title,
        total_comments=len(df),
        language=main_lang,
        topics=topics
    )