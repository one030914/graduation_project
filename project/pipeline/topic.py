from __future__ import annotations
from collections import Counter

from .collect import collect_comments
from configs.schema import TopicsResult, TopicCluster
from model.process.topic.zh import build_topics_zh
from model.process.topic.en import build_topics_en

MIN_TOPIC_COMMENTS = 8
HIGH_NOISE_RATIO = 0.90

def get_topic_language(df) -> str:
    counts = df["language"].value_counts().to_dict()
    zh = counts.get("zh", 0)
    en = counts.get("en", 0)
    supported = zh + en
    if supported <= 0:
        return "unknown"
    if zh > 0 and en > 0 and min(zh, en) / supported >= 0.20:
        return "mixed"
    return "zh" if zh >= en else "en"

def _build_topic_name(keywords: list[str], fallback: str = "未命名主題") -> str:
    words = [str(w).strip() for w in keywords if str(w).strip()]

    if not words:
        return fallback

    return " / ".join(words[:2])

LOW_VALUE_COMMENTS = {
    "讚", "好", "嗯", "+1", "推", "笑死", "哈哈", "哈哈哈",
    "ok", "nice", "good", "lol"
}

def _clean_representative_comments(
    comments: list[str],
    *,
    min_len: int = 3,
    limit: int = 3,
) -> list[str]:
    results = []
    seen = set()

    for text in comments:
        text = str(text or "").replace("\n", " ").replace("\r", " ").strip()
        text = " ".join(text.split())

        if not text:
            continue

        if text.lower() in LOW_VALUE_COMMENTS:
            continue

        if len(text) < min_len:
            continue

        if text in seen:
            continue

        seen.add(text)
        results.append(text)

        if len(results) >= limit:
            break

    return results

def _enrich_topics(topics: list[TopicCluster]) -> list[TopicCluster]:
    for topic in topics:
        topic.topic_name = _build_topic_name(topic.keywords)
        topic.chart_label = topic.topic_name
        topic.representative_comments = _clean_representative_comments(
            topic.representative_comments,
            limit=3,
        )
    return topics

def _build_topic_chart_data(topics: list[TopicCluster]) -> list[dict]:
    return [
        {
            "label": topic.chart_label or topic.topic_name or f"Topic {i + 1}",
            "value": topic.ratio,
            "count": topic.size,
            "keywords": topic.keywords[:5],
            "cluster_id": topic.cluster_id,
        }
        for i, topic in enumerate(topics)
    ]

def _build_top_keywords(topics: list[TopicCluster], limit: int = 12) -> list[str]:
    counter = Counter()

    for topic in topics:
        weight = max(1, topic.size)

        for kw in topic.keywords:
            kw = str(kw).strip()
            if not kw:
                continue
            counter[kw] += weight

    return [kw for kw, _ in counter.most_common(limit)]

def _calc_topic_quality(
    *,
    analyzed_comments: int,
    topics: list[TopicCluster],
) -> dict:
    clustered_comments = sum(topic.size for topic in topics)
    noise_count = max(0, analyzed_comments - clustered_comments)

    coverage_ratio = clustered_comments / max(1, analyzed_comments)
    noise_ratio = noise_count / max(1, analyzed_comments)

    return {
        "clustered_comments": clustered_comments,
        "noise_count": noise_count,
        "coverage_ratio": coverage_ratio,
        "noise_ratio": noise_ratio,
    }

def _get_topics_status(
    *,
    analyzed_comments: int,
    topics: list[TopicCluster],
    noise_ratio: float,
) -> tuple[str, str | None]:
    if analyzed_comments < MIN_TOPIC_COMMENTS:
        return "insufficient_data", "可分析留言數不足，無法形成穩定主題。"

    if not topics:
        return "insufficient_data", "留言內容過於分散，未形成明確主題。"

    if noise_ratio >= HIGH_NOISE_RATIO:
        return "insufficient_data", "多數留言未能形成穩定群組，主題分布僅供參考。"

    if noise_ratio >= 0.70:
        return "ok", "部分留言內容較分散，目前顯示已形成的主要討論群組。"

    if len(topics) == 1:
        return "ok", "留言主要集中在單一主題。"

    return "ok", None

def build_topics(
    url: str,
    *,
    pages: int = 100,
    page_size: int = 100,
    min_likes: int = 1,
) -> TopicsResult:
    comments = collect_comments(url=url, pages=pages, page_size=page_size, min_likes=min_likes)
    return build_topics_from_dataset(comments)

def build_topics_from_dataset(comments) -> TopicsResult:
    if comments.error:
        return TopicsResult(
            url=comments.url,
            title=comments.title,
            status="error",
            message=comments.error,
            error=comments.error,
        )

    df = comments.df.copy()

    if df.empty:
        return TopicsResult(
            url=comments.url,
            title=comments.title,
            total_comments=0,
            analyzed_comments=0,
            status="error",
            message="No comments found",
            error="No comments found",
        )

    df_supported = (
        df[df["language"].isin(("zh", "en"))]
        .drop_duplicates(subset=["clean_text"])
        .copy()
    )
    topic_language = get_topic_language(df_supported)

    analyzed_comments = len(df_supported)

    if analyzed_comments < MIN_TOPIC_COMMENTS:
        return TopicsResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            analyzed_comments=analyzed_comments,
            language=topic_language,
            status="insufficient_data",
            message=(
                f"可分析留言數僅 {analyzed_comments} 則，"
                f"至少需要 {MIN_TOPIC_COMMENTS} 則才能形成較穩定主題。"
            ),
        )

    if topic_language == "unknown":
        return TopicsResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            analyzed_comments=analyzed_comments,
            language=topic_language,
            status="error",
            message="Cannot analyze this language",
            error="Cannot analyze this language",
        )

    topics: list[TopicCluster] = []
    for language, builder in (("zh", build_topics_zh), ("en", build_topics_en)):
        df_lang = df_supported[df_supported["language"] == language].copy()
        if len(df_lang) < 2:
            continue
        topics.extend(builder(df_lang))

    if not topics:
        return TopicsResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            analyzed_comments=analyzed_comments,
            language=topic_language,
            status="insufficient_data",
            message="留言內容過於分散，未形成明確主題。",
        )

    topics = _enrich_topics(topics)
    topics.sort(key=lambda topic: topic.size, reverse=True)
    clustered_total = sum(topic.size for topic in topics)
    for cluster_id, topic in enumerate(topics):
        topic.cluster_id = cluster_id
        topic.ratio = topic.size / max(1, clustered_total)

    quality = _calc_topic_quality(
        analyzed_comments=analyzed_comments,
        topics=topics,
    )

    status, message = _get_topics_status(
        analyzed_comments=analyzed_comments,
        topics=topics,
        noise_ratio=quality["noise_ratio"],
    )

    chart_data = _build_topic_chart_data(topics)
    top_keywords = _build_top_keywords(topics)

    return TopicsResult(
        url=comments.url,
        title=comments.title,
        total_comments=len(df),
        analyzed_comments=analyzed_comments,
        clustered_comments=quality["clustered_comments"],
        noise_count=quality["noise_count"],
        noise_ratio=quality["noise_ratio"],
        coverage_ratio=quality["coverage_ratio"],
        language=topic_language,
        topics=topics,
        chart_data=chart_data,
        top_keywords=top_keywords,
        status=status,
        message=message,
    )
