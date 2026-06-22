from __future__ import annotations

import logging
from typing import Callable

from configs.schema import AnalyzeResult, CommentDataset
from pipeline.collect import collect_comments

from pipeline.emotion import build_emotion_from_dataset
from pipeline.topic import build_topics_from_dataset
from pipeline.timeline import build_timeline_from_dataset
from pipeline.summary import build_summary_from_dataset
from pipeline.keyword import build_keyword_from_dataset
from pipeline.criticism import analyze_comment_criticism_from_dataset
from pipeline.video_content import build_video_content
from agents.analyze_agent import AnalyzeAgent

from scripts.timestamp import Timer

logger = logging.getLogger(__name__)

def _calc_opinion_score(emotion_result) -> int:
    if not emotion_result or not getattr(emotion_result, "stats", None):
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

def _opinion_label(score: int) -> str:
    if score >= 75:
        return "正向偏高"
    if score >= 50:
        return "中性偏穩"
    return "負面偏高"

def _result_status(result) -> str:
    if result is None:
        return "missing"

    if getattr(result, "error", None):
        return "error"

    return getattr(result, "status", "ok")

def _collect_data_sources(**results) -> dict[str, str]:
    return {
        name: _result_status(result)
        for name, result in results.items()
    }

def _collect_data_quality(data_sources: dict[str, str]) -> list[str]:
    display_names = {
        "summary": "摘要",
        "keyword": "關鍵詞",
        "emotion": "情緒",
        "topics": "主題",
        "criticism": "批評",
        "timeline": "時間軸",
        "video_content": "影片內容",
    }

    notes = []

    for name, status in data_sources.items():
        label = display_names.get(name, name)

        if status == "error":
            notes.append(f"{label}分析失敗，主分析已略過該資料來源。")
        elif status == "insufficient_data":
            notes.append(f"{label}資料不足，相關結論僅供參考。")
        elif status == "missing":
            notes.append(f"{label}資料未提供，主分析未納入該來源。")

    return notes

def _dedup(items: list[str], limit: int = 6) -> list[str]:
    results = []
    seen = set()

    for item in items:
        text = str(item or "").strip()
        if not text:
            continue

        if text in seen:
            continue

        seen.add(text)
        results.append(text)

        if len(results) >= limit:
            break

    return results

def _safe_list(value) -> list:
    return value if isinstance(value, list) else []

def _action_texts(items, limit: int = 3) -> list[str]:
    results = []

    for item in _safe_list(items)[:limit]:
        if isinstance(item, dict):
            text = str(item.get("text", "")).strip()
        else:
            text = str(getattr(item, "text", item)).strip()

        if text:
            results.append(text)

    return results

def _build_top_topics(topics_result, limit: int = 5) -> list[str]:
    if getattr(topics_result, "error", None):
        return []

    results = []

    for topic in getattr(topics_result, "topics", [])[:limit]:
        name = (
            getattr(topic, "topic_name", "")
            or getattr(topic, "chart_label", "")
            or " / ".join(getattr(topic, "keywords", [])[:2])
        )

        name = str(name or "").strip()
        if name:
            results.append(name)

    return _dedup(results, limit=limit)

def _build_top_hotspot(timeline_result) -> dict | None:
    if getattr(timeline_result, "status", "ok") != "ok":
        return None

    hotspots = getattr(timeline_result, "hotspots", []) or []
    if not hotspots:
        return None

    hotspot = hotspots[0]

    return {
        "time_label": getattr(hotspot, "time_label", ""),
        "seconds": getattr(hotspot, "seconds", 0),
        "count": getattr(hotspot, "count", 0),
        "representative_comment": (
            getattr(hotspot, "representative_comments", []) or [""]
        )[0],
    }
    
def _build_dashboard_data(
    *,
    emotion,
    topics,
    keyword,
    timeline,
    criticism,
    video_content,
    score: int,
    opinion_label: str,
    main_emotion: str,
) -> dict:
    return {
        "emotion": {
            "opinion_score": score,
            "opinion_label": opinion_label,
            "main_emotion": main_emotion,
            "positive_ratio": getattr(emotion, "positive_ratio", 0.0),
            "negative_ratio": getattr(emotion, "negative_ratio", 0.0),
            "neutral_ratio": getattr(emotion, "neutral_ratio", 0.0),
            "chart_data": getattr(emotion, "chart_data", []) or [],
            "radar_data": getattr(emotion, "radar_data", []) or [],
            "dominant_emotion": getattr(emotion, "dominant_emotion", {}) or {},
            "emotion_ratios": getattr(emotion, "emotion_ratios", {}) or {},
        },
        "topics": {
            "status": _result_status(topics),
            "message": getattr(topics, "message", None),
            "total_comments": getattr(topics, "total_comments", 0),
            "analyzed_comments": getattr(topics, "analyzed_comments", 0),
            "filtered_comments": getattr(topics, "filtered_comments", 0),
            "clustered_comments": getattr(topics, "clustered_comments", 0),
            "noise_count": getattr(topics, "noise_count", 0),
            "coverage_ratio": getattr(topics, "coverage_ratio", 0.0),
            "noise_ratio": getattr(topics, "noise_ratio", 0.0),
            "chart_data": getattr(topics, "chart_data", []) or [],
            "top_keywords": getattr(topics, "top_keywords", []) or [],
            "topics": [
                {
                    "topic_name": (
                        getattr(topic, "topic_name", "")
                        or getattr(topic, "chart_label", "")
                        or " / ".join(getattr(topic, "keywords", [])[:2])
                    ),
                    "size": getattr(topic, "size", 0),
                    "ratio": getattr(topic, "ratio", 0.0),
                    "keywords": getattr(topic, "keywords", [])[:8],
                    "representative_comments": getattr(
                        topic,
                        "representative_comments",
                        [],
                    )[:3],
                }
                for topic in getattr(topics, "topics", [])[:8]
            ],
        },
        "keyword": {
            "chart_data": getattr(keyword, "chart_data", []) or [],
            "wordcloud_data": getattr(keyword, "wordcloud_data", []) or [],
            "top_tags": getattr(keyword, "top_tags", []) or [],
            "keyword_counts": getattr(keyword, "keyword_counts", {}) or {},
            "keyword_ratios": getattr(keyword, "keyword_ratios", {}) or {},
        },
        "timeline": {
            "status": getattr(timeline, "status", ""),
            "message": getattr(timeline, "message", None),
            "bucket_size": getattr(timeline, "bucket_size", 30),
            "peak_count": getattr(timeline, "peak_count", 0),
            "timestamp_comment_count": getattr(
                timeline,
                "timestamp_comment_count",
                0,
            ),
            "timestamp_comment_ratio": getattr(
                timeline,
                "timestamp_comment_ratio",
                0.0,
            ),
            "total_timestamp_mentions": getattr(
                timeline,
                "total_timestamp_mentions",
                0,
            ),
            "chart_data": getattr(timeline, "chart_data", []) or [],
            "hotspots": [
                {
                    "time_label": getattr(hotspot, "time_label", ""),
                    "seconds": getattr(hotspot, "seconds", 0),
                    "count": getattr(hotspot, "count", 0),
                    "representative_comments": getattr(
                        hotspot,
                        "representative_comments",
                        [],
                    )[:3],
                }
                for hotspot in getattr(timeline, "hotspots", [])[:10]
            ],
        },
        "criticism": {
            "status": getattr(criticism, "status", ""),
            "severity_level": getattr(criticism, "severity_level", "low"),
            "criticism_count": getattr(criticism, "criticism_count", 0),
            "reason_count": getattr(criticism, "reason_count", 0),
            "suggestion_count": getattr(criticism, "suggestion_count", 0),
            "chart_data": getattr(criticism, "chart_data", []) or [],
            "main_criticisms": getattr(criticism, "main_criticisms", [])[:5],
            "discontent_reasons": getattr(
                criticism,
                "discontent_reasons",
                [],
            )[:5],
            "suggestions": getattr(criticism, "suggestions", [])[:5],
            "action_items": getattr(criticism, "action_items", [])[:5],
        },
        "video_content": {
            "status": _result_status(video_content),
            "summary_text": getattr(video_content, "summary_text", ""),
            "final_conclusion": getattr(video_content, "final_conclusion", ""),
            "recommended_audience": getattr(
                video_content,
                "recommended_audience",
                "",
            ),
            "action_suggestions": getattr(
                video_content,
                "action_suggestions",
                [],
            )[:5],
            "transcript_word_count": getattr(
                video_content,
                "transcript_word_count",
                0,
            ),
            "transcript_source": getattr(
                video_content,
                "transcript_source",
                None,
            ),
            "chapter_timeline": [
                {
                    "start_seconds": getattr(chapter, "start_seconds", 0),
                    "end_seconds": getattr(chapter, "end_seconds", 0),
                    "title": getattr(chapter, "title", ""),
                    "summary": getattr(chapter, "summary", ""),
                    "keywords": getattr(chapter, "keywords", [])[:5],
                    "importance": getattr(chapter, "importance", "medium"),
                }
                for chapter in getattr(video_content, "chapter_timeline", [])[:8]
            ],
        },
    }

def _build_rule_based_fallback(
    *,
    score: int,
    emotion,
    topics,
    timeline,
    summary,
    keyword,
    criticism,
) -> tuple[list[str], list[str], list[str], list[str]]:
    tags = []
    quick_summary = []
    creator_actions = []
    viewer_tips = []

    opinion = _opinion_label(score)

    if score >= 75:
        tags.append("整體正向")
        quick_summary.append("留言整體風向偏正面，觀眾接受度較高。")
    elif score <= 40:
        tags.append("負面偏高")
        quick_summary.append("留言中負面情緒較明顯，建議優先檢查不滿來源。")
    else:
        tags.append("評價中性")
        quick_summary.append("留言風向相對中性，正反意見並存。")

    summary_points = getattr(summary, "summary_points", []) or []
    if summary_points:
        quick_summary.extend(summary_points[:2])

    top_topics = _build_top_topics(topics, limit=3)
    if top_topics:
        tags.append("熱門主題")
        quick_summary.append(
            f"主要討論集中在「{'、'.join(top_topics[:3])}」等主題。"
        )

    keyword_tags = getattr(keyword, "top_tags", []) or []
    tags.extend(keyword_tags[:5])

    criticism_actions = getattr(criticism, "action_items", []) or []
    creator_actions.extend(criticism_actions[:3])

    severity_level = getattr(criticism, "severity_level", "low")
    if severity_level == "high":
        tags.append("批評強度高")
        quick_summary.append("留言中出現較強批評訊號，建議優先檢查批評與不滿原因。")
    elif severity_level == "medium":
        tags.append("有批評訊號")

    timeline_status = getattr(timeline, "status", "ok")
    hotspots = getattr(timeline, "hotspots", []) or []

    if timeline_status == "ok" and hotspots:
        hotspot = hotspots[0]
        tags.append("有時間軸熱點")
        quick_summary.append(
            f"留言最常提及的影片片段約在 {hotspot.time_label} 附近。"
        )
        viewer_tips.append(
            f"可以優先查看 {hotspot.time_label} 附近，該片段討論度最高。"
        )
    elif timeline_status == "insufficient_data":
        quick_summary.append("本影片留言較少提及具體時間點，因此時間軸熱點僅供參考。")

    return (
        _dedup(tags, limit=8),
        _dedup(quick_summary, limit=5),
        _dedup(creator_actions, limit=5),
        _dedup(viewer_tips, limit=5),
    )

def _build_analyze_result(
    *,
    url: str,
    dataset,
    summary=None,
    keyword=None,
    emotion=None,
    topics=None,
    criticism=None,
    timeline=None,
    video_content=None,
    tags=None,
    quick_summary=None,
    creator_actions=None,
    viewer_tips=None,
    status: str = "running",
    pending_sources: set[str] | None = None,
) -> AnalyzeResult:
    pending_sources = pending_sources or set()
    score = _calc_opinion_score(emotion)
    opinion_label = getattr(emotion, "opinion_label", "") or _opinion_label(score)
    dominant = getattr(emotion, "dominant_emotion", {}) or {}
    main_emotion = dominant.get("display_name") or dominant.get("label") or ""
    top_topics = _build_top_topics(topics, limit=5)
    top_hotspot = _build_top_hotspot(timeline)
    data_sources = _collect_data_sources(
        summary=summary,
        keyword=keyword,
        emotion=emotion,
        topics=topics,
        criticism=criticism,
        timeline=timeline,
        video_content=video_content,
    )

    for source in pending_sources:
        data_sources[source] = "pending"

    data_quality = _collect_data_quality(data_sources)
    dashboard_data = _build_dashboard_data(
        emotion=emotion,
        topics=topics,
        keyword=keyword,
        timeline=timeline,
        criticism=criticism,
        video_content=video_content,
        score=score,
        opinion_label=opinion_label,
        main_emotion=main_emotion,
    )

    return AnalyzeResult(
        video_id=getattr(dataset, "video_id", ""),
        title=(
            getattr(dataset, "title", "")
            or getattr(emotion, "title", "")
            or getattr(topics, "title", "")
            or getattr(summary, "title", "")
            or getattr(keyword, "title", "")
            or getattr(criticism, "title", "")
            or getattr(timeline, "title", "")
        ),
        url=url,
        status=status,
        total_comments=len(getattr(dataset, "df", [])) if dataset is not None else 0,
        public_opinion_score=score,
        opinion_label=opinion_label,
        main_emotion=main_emotion,
        timeline_status=getattr(timeline, "status", data_sources.get("timeline", "")),
        tags=_dedup((tags or []) + (getattr(keyword, "top_tags", []) or [])[:5], limit=8),
        quick_summary=_dedup(quick_summary or [], limit=5),
        top_topics=_dedup(top_topics, limit=5),
        top_hotspot=top_hotspot,
        creator_actions=_dedup(creator_actions or [], limit=5),
        viewer_tips=_dedup(viewer_tips or [], limit=5),
        data_sources=data_sources,
        data_quality=data_quality,
        dashboard_data=dashboard_data,
    )

def build_analyze(url: str, on_partial: Callable[[AnalyzeResult], None] | None = None) -> AnalyzeResult:
    timer = Timer()

    # 時間軸需要保留重複留言中的時間戳訊號；其他分析則使用去重後資料避免同一句話放大權重。
    timeline_dataset = collect_comments(
        url,
        pages=15,
        page_size=100,
        min_likes=0,
        order="relevance",
        recent_pages=5,
        duplicate=True,
    )
    
    timer.mark("collect_comments")

    if timeline_dataset.error:
        return AnalyzeResult(
            video_id=timeline_dataset.video_id,
            title=timeline_dataset.title,
            url=url,
            status="error",
            message=timeline_dataset.error,
            error=timeline_dataset.error,
        )

    dataset = CommentDataset(
        video_id=timeline_dataset.video_id,
        title=timeline_dataset.title,
        url=timeline_dataset.url,
        df=timeline_dataset.df.drop_duplicates(subset=["clean_text"]).copy(),
        duration_seconds=getattr(timeline_dataset, "duration_seconds", None),
        error=None,
    )
    timer.mark("prepare_analysis_dataset")

    summary = None
    keyword = None
    emotion = None
    topics = None
    criticism = None
    timeline = None
    video_content = None

    pending_sources = {
        "summary",
        "keyword",
        "emotion",
        "topics",
        "criticism",
        "timeline",
        "video_content",
    }

    def publish_partial() -> None:
        # 綜合分析耗時較長，先把已完成的子分析包成同一種 AnalyzeResult 給前端漸進顯示。
        if on_partial is None:
            return
        on_partial(
            _build_analyze_result(
                url=url,
                dataset=dataset,
                summary=summary,
                keyword=keyword,
                emotion=emotion,
                topics=topics,
                criticism=criticism,
                timeline=timeline,
                video_content=video_content,
                status="running",
                pending_sources=pending_sources,
            )
        )

    publish_partial()

    emotion = build_emotion_from_dataset(dataset)
    pending_sources.discard("emotion")
    timer.mark("build_emotion")
    publish_partial()
    
    topics = build_topics_from_dataset(dataset)
    pending_sources.discard("topics")
    timer.mark("build_topics")
    publish_partial()

    summary = build_summary_from_dataset(dataset)
    pending_sources.discard("summary")
    timer.mark("build_summary")
    publish_partial()

    keyword = build_keyword_from_dataset(dataset)
    pending_sources.discard("keyword")
    timer.mark("build_keyword")
    publish_partial()

    criticism = analyze_comment_criticism_from_dataset(dataset)
    pending_sources.discard("criticism")
    timer.mark("analyze_criticism")
    publish_partial()

    timeline = build_timeline_from_dataset(timeline_dataset)
    pending_sources.discard("timeline")
    timer.mark("build_timeline")
    publish_partial()
    
    try:
        video_content = build_video_content(url)
    except Exception as exc:
        logger.exception("Video content analysis failed: %s", exc)
    pending_sources.discard("video_content")
    timer.mark("build_video_content")
    publish_partial()

    score = _calc_opinion_score(emotion)
    opinion_label = getattr(emotion, "opinion_label", "") or _opinion_label(score)

    data_sources = _collect_data_sources(
        summary=summary,
        keyword=keyword,
        emotion=emotion,
        topics=topics,
        criticism=criticism,
        timeline=timeline,
        video_content=video_content,
    )
    data_quality = _collect_data_quality(data_sources)

    tags, quick_summary, creator_actions, viewer_tips = _build_rule_based_fallback(
        score=score,
        emotion=emotion,
        topics=topics,
        timeline=timeline,
        summary=summary,
        keyword=keyword,
        criticism=criticism,
    )

    agent_payload = {
        "task": "main_insight_integration",
        "instructions": {
            "goal": "整合子分析，產生主分析洞察。",
            "do_not": [
                "不要重新分類留言",
                "不要捏造資料中沒有的批評、問題或影片內容",
                "不要把資料不足解讀成風向良好",
                "不要在主題分析資料不足或覆蓋率偏低時，硬推論完整留言區主題共識",
            ],
            "output_usage": {
                "quick_summary": "給 Discord 主分析智慧快報使用",
                "tags": "給 Discord 標籤使用，必須短",
                "creator_actions": "給創作者的具體行動建議",
                "viewer_tips": "給觀眾或使用者的觀看提示",
            },
        },
        "data_sources": data_sources,
        "data_quality": data_quality,
        "summary_context": {
            "label": "留言摘要",
            "purpose": "提供留言區整體討論脈絡。",
            "status": _result_status(summary),
            "summary_points": getattr(summary, "summary_points", [])[:3],
        },
        "emotion_context": {
            "label": "情緒與風向",
            "purpose": "判斷留言區整體情緒、輿情溫度與主導情緒。",
            "status": _result_status(emotion),
            "public_opinion_score": score,
            "opinion_label": opinion_label,
            "dominant_emotion": getattr(emotion, "dominant_emotion", {}),
            "emotion_ratios": getattr(emotion, "emotion_ratios", {}),
        },
        "topic_context": {
            "label": "熱門討論主題",
            "purpose": "指出留言區最主要的討論焦點。",
            "status": _result_status(topics),
            "message": getattr(topics, "message", None),
            "total_comments": getattr(topics, "total_comments", 0),
            "analyzed_comments": getattr(topics, "analyzed_comments", 0),
            "filtered_comments": getattr(topics, "filtered_comments", 0),
            "clustered_comments": getattr(topics, "clustered_comments", 0),
            "coverage_ratio": getattr(topics, "coverage_ratio", 0.0),
            "noise_ratio": getattr(topics, "noise_ratio", 0.0),
            "guidance": (
                "若 status 不是 ok，或 coverage_ratio 偏低，"
                "主分析只能保守引用主題結果，不能把它當成完整留言區共識。"
            ),
            "top_topics": [
                {
                    "topic_name": (
                        getattr(t, "topic_name", "")
                        or getattr(t, "chart_label", "")
                        or " / ".join(getattr(t, "keywords", [])[:2])
                    ),
                    "keywords": getattr(t, "keywords", [])[:3],
                    "ratio": getattr(t, "ratio", 0.0),
                    "representative_comments": getattr(t, "representative_comments", [])[:1],
                }
                for t in getattr(topics, "topics", [])[:3]
            ] if not getattr(topics, "error", None) else [],
        },

        "criticism_context": {
            "label": "批評與改善訊號",
            "purpose": "整理留言中的批評、不滿原因與可改善方向。",
            "status": _result_status(criticism),
            "severity_level": getattr(criticism, "severity_level", "low"),
            "main_criticisms": getattr(criticism, "main_criticisms", [])[:3],
            "discontent_reasons": getattr(criticism, "discontent_reasons", [])[:3],
            "suggestions": getattr(criticism, "suggestions", [])[:3],
            "action_items": getattr(criticism, "action_items", [])[:3],
        },
        "keyword_context": {
            "label": "熱門關鍵詞與標籤",
            "purpose": "提供標籤、文字雲與熱門詞依據。",
            "status": _result_status(keyword),
            "top_tags": getattr(keyword, "top_tags", [])[:6],
        },
        "timeline_context": {
            "label": "時間軸熱點",
            "purpose": "指出觀眾主動提及的影片時間點。",
            "status": _result_status(timeline),
            "message": getattr(timeline, "message", ""),
            "timestamp_comment_count": getattr(timeline, "timestamp_comment_count", 0),
            "timestamp_comment_ratio": getattr(timeline, "timestamp_comment_ratio", 0.0),
            "hotspots": [
                {
                    "time_label": getattr(h, "time_label", ""),
                    "count": getattr(h, "count", 0),
                    "representative_comments": getattr(h, "representative_comments", [])[:1],
                }
                for h in getattr(timeline, "hotspots", [])[:3]
            ],
        },
        "video_content": {
            "label": "影片內容脈絡",
            "purpose": "提供影片主題、內容摘要、章節與創作者建議，用來校正留言解讀，避免只靠留言誤判影片內容。",
            "status": _result_status(video_content),
            "summary_text": getattr(video_content, "summary_text", ""),
            "final_conclusion": getattr(video_content, "final_conclusion", ""),
            "recommended_audience": getattr(video_content, "recommended_audience", ""),
            "action_suggestions": getattr(video_content, "action_suggestions", [])[:3],
            "chapter_timeline": [
                {
                    "title": getattr(chapter, "title", ""),
                    "summary": getattr(chapter, "summary", ""),
                    "importance": getattr(chapter, "importance", "medium"),
                }
                for chapter in getattr(video_content, "chapter_timeline", [])[:3]
            ],
        }
    }

    try:
        agent_result = AnalyzeAgent().analyze(agent_payload)

        quick_summary = agent_result.get("quick_summary") or quick_summary
        tags = agent_result.get("tags") or tags
        creator_actions = agent_result.get("creator_actions") or creator_actions
        viewer_tips = agent_result.get("viewer_tips") or viewer_tips

    except Exception as e:
        logger.exception("AnalyzeAgent failed, fallback to rule-based result: %s", e)
        
    timer.mark("analyze_agent")

    logger.info("Analyze timing report:\n%s", timer.report())
    logger.info("Analyze total time: %s seconds", timer.total())

    return _build_analyze_result(
        url=url,
        dataset=dataset,
        summary=summary,
        keyword=keyword,
        emotion=emotion,
        topics=topics,
        criticism=criticism,
        timeline=timeline,
        video_content=video_content,
        tags=tags,
        quick_summary=quick_summary,
        creator_actions=creator_actions,
        viewer_tips=viewer_tips,
        status="ok",
    )
