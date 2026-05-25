from __future__ import annotations

from configs.schema import AnalyzeResult
from pipeline.collect import collect_comments

from pipeline.emotion import build_emotion_from_dataset
from pipeline.topic import build_topics_from_dataset
from pipeline.timeline import build_timeline_from_dataset
from pipeline.summary import build_summary_from_dataset
from pipeline.keyword import build_keyword_from_dataset
from pipeline.criticism import analyze_comment_criticism_from_dataset
from agents.analyze_agent import AnalyzeAgent

from scripts.timestamp import Timer

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

def build_analyze(url: str) -> AnalyzeResult:
    timer = Timer()
    
    dataset = collect_comments(
        url,
        pages=100,
        page_size=100,
        min_likes=0,
        order="relevance",
    )
    
    timer.mark("collect_comments")

    if dataset.error:
        return AnalyzeResult(
            video_id=dataset.video_id,
            title=dataset.title,
            url=url,
            status="error",
            message=dataset.error,
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

    timer.mark("collect_timeline_comments")

    emotion = build_emotion_from_dataset(dataset)
    
    timer.mark("build_emotion")
    
    topics = build_topics_from_dataset(dataset)
    
    timer.mark("build_topics")

    summary = build_summary_from_dataset(dataset)

    timer.mark("build_summary")

    keyword = build_keyword_from_dataset(dataset)

    timer.mark("build_keyword")

    criticism = analyze_comment_criticism_from_dataset(dataset)

    timer.mark("analyze_criticism")

    timeline = build_timeline_from_dataset(timeline_dataset)
    
    timer.mark("build_timeline")

    title = (
        dataset.title
        or getattr(emotion, "title", "")
        or getattr(topics, "title", "")
        or getattr(summary, "title", "")
        or getattr(keyword, "title", "")
        or getattr(criticism, "title", "")
        or getattr(timeline, "title", "")
    )

    video_id = dataset.video_id
    score = _calc_opinion_score(emotion)
    opinion_label = getattr(emotion, "opinion_label", "") or _opinion_label(score)

    top_topics = _build_top_topics(topics, limit=5)
    top_hotspot = _build_top_hotspot(timeline)

    data_sources = _collect_data_sources(
        summary=summary,
        keyword=keyword,
        emotion=emotion,
        topics=topics,
        criticism=criticism,
        timeline=timeline,
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
            "summary_points": getattr(summary, "summary_points", [])[:5],
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
            "top_topics": [
                {
                    "topic_name": (
                        getattr(t, "topic_name", "")
                        or getattr(t, "chart_label", "")
                        or " / ".join(getattr(t, "keywords", [])[:2])
                    ),
                    "keywords": getattr(t, "keywords", [])[:5],
                    "ratio": getattr(t, "ratio", 0.0),
                    "representative_comments": getattr(t, "representative_comments", [])[:2],
                }
                for t in getattr(topics, "topics", [])[:3]
            ] if not getattr(topics, "error", None) else [],
        },

        "criticism_context": {
            "label": "批評與改善訊號",
            "purpose": "整理留言中的批評、不滿原因與可改善方向。",
            "status": _result_status(criticism),
            "severity_level": getattr(criticism, "severity_level", "low"),
            "main_criticisms": getattr(criticism, "main_criticisms", [])[:5],
            "discontent_reasons": getattr(criticism, "discontent_reasons", [])[:5],
            "suggestions": getattr(criticism, "suggestions", [])[:5],
            "action_items": getattr(criticism, "action_items", [])[:5],
        },
        "keyword_context": {
            "label": "熱門關鍵詞與標籤",
            "purpose": "提供標籤、文字雲與熱門詞依據。",
            "status": _result_status(keyword),
            "top_tags": getattr(keyword, "top_tags", [])[:10],
            "chart_data": getattr(keyword, "chart_data", [])[:10],
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
                    "representative_comments": getattr(h, "representative_comments", [])[:2],
                }
                for h in getattr(timeline, "hotspots", [])[:3]
            ],
        },
    }

    try:
        agent_result = AnalyzeAgent().analyze(agent_payload)

        quick_summary = agent_result.get("quick_summary") or quick_summary
        tags = agent_result.get("tags") or tags
        creator_actions = agent_result.get("creator_actions") or creator_actions
        viewer_tips = agent_result.get("viewer_tips") or viewer_tips

    except Exception as e:
        print(f"AnalyzeAgent failed, fallback to rule-based result: {e}")
        
    timer.mark("analyze_agent")

    dominant = getattr(emotion, "dominant_emotion", {}) or {}
    main_emotion = (
        dominant.get("display_name")
        or dominant.get("label")
        or ""
    )
    
    print("=== ANALYZE TIMING REPORT ===\n")
    print(timer.report())

    return AnalyzeResult(
        video_id=video_id,
        title=title,
        url=url,

        status="ok",
        message=None,

        total_comments=len(dataset.df),

        public_opinion_score=score,
        opinion_label=opinion_label,

        main_emotion=main_emotion,
        timeline_status=getattr(timeline, "status", ""),

        tags=_dedup(tags + getattr(keyword, "top_tags", [])[:5], limit=8),
        quick_summary=_dedup(quick_summary, limit=5),

        top_topics=_dedup(top_topics, limit=5),
        top_hotspot=top_hotspot,

        creator_actions=_dedup(creator_actions, limit=5),
        viewer_tips=_dedup(viewer_tips, limit=5),

        data_sources=data_sources,
        data_quality=data_quality,
    )