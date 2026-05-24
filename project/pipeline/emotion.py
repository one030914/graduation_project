from collections import Counter
from typing import Any

from .collect import collect_comments
from configs.schema import EmotionResult, EmotionStats
from model.process.emotion.zh import analyze_emotion_zh
from model.process.emotion.en import analyze_emotion_en

EMOTION_CLASSES = [
    "Joy",
    "Angry",
    "Sad",
    "Surprised",
    "Disgusted",
    "Neutral",
]

EMOTION_DISPLAY_NAMES = {
    "Joy": "喜悅/支持",
    "Angry": "憤怒/不滿",
    "Sad": "悲傷/遺憾",
    "Surprised": "驚訝",
    "Disgusted": "反感/強烈不滿",
    "Neutral": "中性",
}

SUPPORT_KEYWORDS = [
    "支持", "加油", "感謝", "謝謝", "respect", "thanks", "support"
]

def _has_support_signal(text: str) -> bool:
    text = str(text or "").lower()
    return any(kw.lower() in text for kw in SUPPORT_KEYWORDS)

def _safe_int(value: Any) -> int:
    try:
        if value is None:
            return 0
        return int(value)
    except Exception:
        return 0

def _build_emotion_ratios(emotions: dict[str, int], total: int) -> dict[str, float]:
    denominator = max(1, total)

    return {
        label: emotions.get(label, 0) / denominator
        for label in EMOTION_CLASSES
    }

def _calc_sentiment_ratios(ratios: dict[str, float]) -> tuple[float, float, float]:
    positive_ratio = (
        ratios.get("Joy", 0.0)
        + ratios.get("Surprised", 0.0) * 0.5
    )

    negative_ratio = (
        ratios.get("Angry", 0.0)
        + ratios.get("Sad", 0.0) * 0.7
        + ratios.get("Disgusted", 0.0)
    )

    neutral_ratio = ratios.get("Neutral", 0.0)

    return positive_ratio, negative_ratio, neutral_ratio

def _calc_opinion_score(ratios: dict[str, float]) -> int:
    score = 50.0

    score += ratios.get("Joy", 0.0) * 35
    score += ratios.get("Surprised", 0.0) * 10

    score -= ratios.get("Angry", 0.0) * 35
    score -= ratios.get("Sad", 0.0) * 20
    score -= ratios.get("Disgusted", 0.0) * 30

    return int(max(0, min(100, round(score))))

def _get_opinion_label(score: int) -> str:
    if score >= 80:
        return "高度正向"
    if score >= 65:
        return "正向偏高"
    if score >= 45:
        return "中性 / 意見分歧"
    if score >= 30:
        return "負面偏高"
    return "高度負面"

def _build_dominant_emotion(
    emotions: dict[str, int],
    ratios: dict[str, float],
) -> dict[str, Any]:
    if not emotions:
        return {}

    dominant_label = max(emotions, key=emotions.get)

    return {
        "label": dominant_label,
        "display_name": EMOTION_DISPLAY_NAMES.get(dominant_label, dominant_label),
        "count": emotions.get(dominant_label, 0),
        "ratio": ratios.get(dominant_label, 0.0),
    }

def _build_chart_data(
    emotions: dict[str, int],
    ratios: dict[str, float],
) -> list[dict[str, Any]]:
    return [
        {
            "key": label,
            "label": EMOTION_DISPLAY_NAMES.get(label, label),
            "value": ratios.get(label, 0.0),
            "count": emotions.get(label, 0),
        }
        for label in EMOTION_CLASSES
    ]

def _build_radar_data(ratios: dict[str, float]) -> list[dict[str, Any]]:
    return [
        {
            "key": "praise",
            "label": "喜悅/稱讚",
            "value": ratios.get("Joy", 0.0),
        },
        {
            "key": "criticism",
            "label": "憤怒/批評",
            "value": ratios.get("Angry", 0.0) + ratios.get("Disgusted", 0.0),
        },
        {
            "key": "sadness",
            "label": "悲傷",
            "value": ratios.get("Sad", 0.0),
        },
        {
            "key": "surprise",
            "label": "驚訝",
            "value": ratios.get("Surprised", 0.0),
        },
        {
            "key": "neutral",
            "label": "中性",
            "value": ratios.get("Neutral", 0.0),
        },
    ]

def _get_emotion_status(analyzed_comments: int) -> tuple[str, str | None]:
    if analyzed_comments <= 0:
        return "error", "No comments for emotion analysis"

    if analyzed_comments < 10:
        return "insufficient_data", "可分析留言數過少，情緒分析僅供參考。"

    if analyzed_comments < 50:
        return "insufficient_data", "可分析留言數偏少，情緒分布可能不穩定。"

    return "ok", None

def _get_representative_comments(
    df,
    label: str,
    *,
    limit: int = 3,
) -> list[dict[str, Any]]:
    if "emotion_label" not in df.columns:
        return []

    sub = df[df["emotion_label"] == label].copy()

    if sub.empty:
        return []

    sub["text_len"] = sub["clean_text"].astype(str).str.len()
    sub = sub[sub["text_len"] >= 6]

    if sub.empty:
        return []

    sub["like_count_safe"] = sub["like_count"].apply(_safe_int)
    sub["reply_count_safe"] = sub["reply_count"].apply(_safe_int)
    sub["support_signal"] = sub["raw_text"].astype(str).apply(_has_support_signal)

    if label in {"Angry", "Disgusted", "Sad"}:
        sub = sub.sort_values(
            by=["support_signal", "like_count_safe", "reply_count_safe", "text_len"],
            ascending=[True, False, False, False],
        )
    else:
        sub = sub.sort_values(
            by=["like_count_safe", "reply_count_safe", "text_len"],
            ascending=[False, False, False],
        )

    results = []

    for _, row in sub.head(limit).iterrows():
        text = str(row.get("raw_text") or row.get("clean_text") or "").strip()

        if not text:
            continue

        results.append({
            "text": text,
            "like_count": _safe_int(row.get("like_count", 0)),
            "reply_count": _safe_int(row.get("reply_count", 0)),
            "comment_id": row.get("comment_id"),
        })

    return results

def _build_representative_comments(df) -> dict[str, list[dict[str, Any]]]:
    return {
        label: _get_representative_comments(df, label, limit=3)
        for label in EMOTION_CLASSES
    }

def get_main_language(df) -> str:
    counts = df["language"].value_counts().to_dict()
    zh = counts.get("zh", 0)
    en = counts.get("en", 0)
    unknown = counts.get("unknown", 0)
    return "zh" if zh >= en and zh >= unknown else "en" if en >= zh and en >= unknown else "unknown"

def build_emotion(
    url: str,
    *,
    pages: int = 5,
    page_size: int = 100,
    min_likes: int = 1,
) -> EmotionResult:
    comments = collect_comments(url=url, pages=pages, page_size=page_size, min_likes=min_likes)
    return build_emotion_from_dataset(comments)

def build_emotion_from_dataset(comments) -> EmotionResult:
    if comments.error:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            status="error",
            message=comments.error,
            error=comments.error,
        )

    df = comments.df.copy()

    if df.empty:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            total_comments=0,
            analyzed_comments=0,
            skipped_comments=0,
            language="unknown",
            status="error",
            message="No comments found",
            error="No comments found",
        )

    main_lang = get_main_language(df)
    df_lang = df[df["language"] == main_lang].copy()

    if main_lang == "zh":
        df_lang = df_lang[
            df_lang["clean_text"].astype(str).str.strip().str.len() >= 2
        ].copy()
        texts = df_lang["clean_text"].tolist()
        labels = analyze_emotion_zh(texts)

    elif main_lang == "en":
        df_lang = df_lang[
            df_lang["clean_text"].astype(str).str.strip().str.split().str.len() >= 1
        ].copy()
        texts = df_lang["clean_text"].tolist()
        labels = analyze_emotion_en(texts)

    else:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            analyzed_comments=0,
            skipped_comments=len(df),
            language=main_lang,
            status="error",
            message="Cannot analyze this language",
            error="Cannot analyze this language",
        )

    if not labels:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            analyzed_comments=0,
            skipped_comments=len(df),
            language=main_lang,
            status="error",
            message="No comments for emotion analysis",
            error="No comments for emotion analysis",
        )

    df_lang = df_lang.iloc[:len(labels)].copy()
    df_lang["emotion_label"] = labels

    counter = Counter(labels)
    emotions = {k: counter.get(k, 0) for k in EMOTION_CLASSES}

    analyzed_comments = len(labels)
    skipped_comments = max(0, len(df) - analyzed_comments)

    ratios = _build_emotion_ratios(emotions, analyzed_comments)

    positive_ratio, negative_ratio, neutral_ratio = _calc_sentiment_ratios(ratios)

    opinion_score = _calc_opinion_score(ratios)
    opinion_label = _get_opinion_label(opinion_score)

    dominant_emotion = _build_dominant_emotion(emotions, ratios)

    chart_data = _build_chart_data(emotions, ratios)
    radar_data = _build_radar_data(ratios)

    representative_comments = _build_representative_comments(df_lang)

    status, message = _get_emotion_status(analyzed_comments)

    stats = EmotionStats(
        emotions=emotions,
        ratios=ratios,
        total=analyzed_comments,
    )

    return EmotionResult(
        url=comments.url,
        title=comments.title,
        total_comments=len(df),
        analyzed_comments=analyzed_comments,
        skipped_comments=skipped_comments,
        language=main_lang,
        status=status,
        message=message,
        stats=stats,
        emotion_ratios=ratios,
        opinion_score=opinion_score,
        opinion_label=opinion_label,
        positive_ratio=positive_ratio,
        negative_ratio=negative_ratio,
        neutral_ratio=neutral_ratio,
        dominant_emotion=dominant_emotion,
        chart_data=chart_data,
        radar_data=radar_data,
        representative_comments=representative_comments,
    )
