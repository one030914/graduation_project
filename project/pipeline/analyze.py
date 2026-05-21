from __future__ import annotations

from configs.schema import AnalyzeResult
from pipeline.emotion import build_emotion
from pipeline.intent import build_intent
from pipeline.timeline import build_timeline
from pipeline.topic import build_topics


def _calc_opinion_score(emotion_result) -> int:
    if not emotion_result or not emotion_result.stats:
        return 50

    emotions = emotion_result.stats.emotions or {}
    total = max(1, emotion_result.stats.total)

    positive = emotions.get("Joy", 0) + emotions.get("Surprised", 0)
    negative = emotions.get("Angry", 0) + emotions.get("Sad", 0) + emotions.get("Disgusted", 0)

    score = 50 + int((positive - negative) / total * 50)
    return max(0, min(100, score))


def _opinion_label(score: int) -> str:
    if score >= 75:
        return "正向偏高"
    if score >= 50:
        return "中性偏穩"
    return "負面偏高"


def build_analyze(url: str) -> AnalyzeResult:
    emotion = build_emotion(url)
    topics = build_topics(url)
    intent = build_intent(url)
    timeline = build_timeline(url)

    title = (
        getattr(emotion, "title", "")
        or getattr(topics, "title", "")
        or getattr(intent, "title", "")
        or getattr(timeline, "title", "")
    )

    video_id = (
        getattr(intent, "video_id", "")
        or getattr(timeline, "video_id", "")
        or ""
    )

    total_comments = max(
        int(getattr(emotion, "total_comments", 0) or 0),
        int(getattr(topics, "total_comments", 0) or 0),
        int(getattr(intent, "total_comments", 0) or 0),
        int(getattr(timeline, "total_comments", 0) or 0),
    )

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

    if not getattr(timeline, "error", None) and timeline.hotspots:
        hotspot = timeline.hotspots[0]
        top_hotspot = {
            "time_label": hotspot.time_label,
            "seconds": hotspot.seconds,
            "count": hotspot.count,
            "representative_comment": (hotspot.representative_comments or [""])[0],
        }
        quick_summary.append(f"留言最常提及的影片片段約在 {hotspot.time_label} 附近。")
        viewer_tips.append(f"可以優先查看 {hotspot.time_label} 附近，該片段討論度最高。")
        tags.append("有時間軸熱點")

    return AnalyzeResult(
        video_id=video_id,
        title=title,
        url=url,
        total_comments=total_comments,
        public_opinion_score=score,
        opinion_label=_opinion_label(score),
        tags=list(dict.fromkeys(tags))[:6],
        quick_summary=quick_summary[:5],
        top_topics=top_topic_keywords,
        top_hotspot=top_hotspot,
        creator_actions=creator_actions[:5],
        viewer_tips=viewer_tips[:5],
    )
