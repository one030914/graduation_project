from __future__ import annotations

from .collect import collect_comments
from configs.schema import TopicsResult, TopicCluster
from model.process.topic.zh import build_topics_zh
from model.process.topic.en import build_topics_en

def get_main_language(df) -> str:
    counts = df["language"].value_counts().to_dict()
    zh = counts.get("zh", 0)
    en = counts.get("en", 0)
    unknown = counts.get("unknown", 0)
    return "zh" if zh >= en and zh >= unknown else "en" if en >= zh and en >= unknown else "unknown"

def build_topics(
    url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 1,
) -> TopicsResult:
    comments = collect_comments(url=url, pages=pages, page_size=page_size, min_likes=min_likes)
    if comments.error:
        return TopicsResult(url=url, error=comments.error)

    df = comments.df.copy()

    main_lang = get_main_language(df)
    df_lang = df[df["language"] == main_lang].copy()
        
    if len(df_lang) < 15:
        return TopicsResult(
            url=url,
            title=comments.title,
            error="Not enough comments to form stable topics"
        )

    if main_lang == "zh":
        topics = build_topics_zh(df_lang)
    elif main_lang == "en":
        topics = build_topics_en(df_lang)
    else:
        return TopicsResult(
            url=url,
            title=comments.title,
            error="Cannot analyze this language"
        )
    
    if not topics:
        return TopicsResult(
            url=url,
            title=comments.title,
            error="No clear topics formed"
        )

    return TopicsResult(
        url=url,
        title=comments.title,
        total_comments=len(df_lang),
        language=main_lang,
        topics=topics
    )