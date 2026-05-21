from collections import Counter

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
            error=comments.error,
        )

    df = comments.df.copy()

    main_lang = get_main_language(df)
    df_lang = df[df["language"] == main_lang].copy()
    texts = df_lang["clean_text"].tolist()

    # 情緒分類前可先做簡單過濾，避免太短句干擾
    if main_lang == "zh":
        texts = [t for t in texts if len(str(t).strip()) >= 2]
        labels = analyze_emotion_zh(texts)
    elif main_lang == "en":
        texts = [t for t in texts if len(str(t).strip().split()) >= 1]
        labels = analyze_emotion_en(texts)
    else:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            language=main_lang,
            error="Cannot analyze this language"
        )

    if not labels:
        return EmotionResult(
            url=comments.url,
            title=comments.title,
            total_comments=len(df),
            language=main_lang,
            error="No comments for emotion analysis"
        )

    counter = Counter(labels)
    emotions = {k: counter.get(k, 0) for k in EMOTION_CLASSES}

    stats = EmotionStats(
        emotions=emotions,
        total=len(labels),
    )

    return EmotionResult(
        url=comments.url,
        title=comments.title,
        total_comments=len(df),
        language=main_lang,
        stats=stats,
    )
