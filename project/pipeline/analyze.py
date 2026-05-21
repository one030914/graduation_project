from __future__ import annotations

from configs.schema import AnalyzeResult
from pipeline.collect import collect_comments
from pipeline.emotion import build_emotion_from_dataset
from pipeline.topic import build_topics_from_dataset
from pipeline.intent import build_intent_from_dataset
from pipeline.timeline import build_timeline_from_dataset


def _calc_opinion_score(emotion_result) -> int:
    if not emotion_result or not emotion_result.stats:
        return 50

    emotions = emotion_result.stats.emotions or {}
    total = max(1, emotion_result.stats.total)

    positive = emotions.get("Joy", 0) + emotions.get("Surprised", 0)
    negative = (
        emotions.get("Angry", 0)
        + emotions.get("Sad", 0)
        + emotions.get("Disgusted", 0)
    )

    score = 50 + int((positive - negative) / total * 50)
    return max(0, min(100, score))


def build_analyze(url: str) -> AnalyzeResult:
    dataset = collect_comments(
        url,
        pages=100,
        page_size=100,
        min_likes=0,
        order="relevance",
    )

    if dataset.error:
        return AnalyzeResult(
            video_id=dataset.video_id,
            title=dataset.title,
            url=url,
            error=dataset.error,
        )

    timeline_dataset = collect_comments(
        url,
        pages=100,
        page_size=100,
        min_likes=0,
        order="relevance",
        duplicate=True,
    )

    emotion = build_emotion_from_dataset(dataset)
    topics = build_topics_from_dataset(dataset)
    intent = build_intent_from_dataset(dataset)
    timeline = build_timeline_from_dataset(timeline_dataset)

    title = (
        dataset.title
        or getattr(emotion, "title", "")
        or getattr(topics, "title", "")
        or getattr(intent, "title", "")
        or getattr(timeline, "title", "")
    )

    video_id = dataset.video_id

    score = _calc_opinion_score(emotion)

    tags = []
    quick_summary = []
    creator_actions = []
    viewer_tips = []
    top_topic_keywords = []
    top_hotspot = None

    if score >= 75:
        tags.append("整體正向")
        quick_summary.append("留言整體風向偏正面，觀眾接受度高。")
    elif score <= 40:
        tags.append("負面偏高")
        quick_summary.append("留言中負面情緒較明顯，建議檢查主要不滿來源。")
    else:
        tags.append("評價中性")
        quick_summary.append("留言風向較中性，正反意見並存。")

    if not getattr(topics, "error", None) and topics.topics:
        top_topic = topics.topics[0]
        top_topic_keywords = top_topic.keywords[:5]
        kw = "、".join(top_topic.keywords[:3])
        tags.append("熱門主題")
        quick_summary.append(f"主要討論集中在「{kw}」等關鍵詞。")

    if not getattr(intent, "error", None):
        if intent.questions:
            creator_actions.append("優先回覆高讚提問，降低觀眾疑惑。")
            tags.append("提問量高")

        if intent.corrections:
            creator_actions.append("檢查高讚勘誤留言，必要時補充說明或置頂修正。")
            tags.append("可能有勘誤")

        if intent.wishlist:
            creator_actions.append("整理觀眾許願內容，作為下一支影片題材參考。")
            tags.append("有續集需求")

        if intent.resources:
            viewer_tips.append("留言中包含外部資源連結，可作為補充資料參考。")

    timeline_status = getattr(timeline, "status", "ok")

    if timeline_status == "ok" and timeline.hotspots:
        hotspot = timeline.hotspots[0]
        top_hotspot = {
            "time_label": hotspot.time_label,
            "seconds": hotspot.seconds,
            "count": hotspot.count,
            "representative_comment": (hotspot.representative_comments or [""])[0],
        }
        quick_summary.append(
            f"留言最常提及的影片片段約在 {hotspot.time_label} 附近。"
        )
        viewer_tips.append(
            f"可以優先查看 {hotspot.time_label} 附近，該片段討論度最高。"
        )
        tags.append("有時間軸熱點")
    elif timeline_status == "insufficient_data":
        quick_summary.append(
            "本影片留言較少提及具體時間點，因此未納入時間軸熱點判斷。"
        )

    return AnalyzeResult(
        video_id=video_id,
        title=title,
        url=url,
        total_comments=len(dataset.df),
        public_opinion_score=score,
        tags=list(dict.fromkeys(tags))[:6],
        quick_summary=quick_summary[:5],
        top_topics=top_topic_keywords,
        top_hotspot=top_hotspot,
        creator_actions=creator_actions[:5],
        viewer_tips=viewer_tips[:5],
    )
