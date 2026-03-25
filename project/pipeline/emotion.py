from collections import Counter

from data.youtube.api import API
from data.preprocess.pipeline import batch_preprocess_comments
from pipeline.schema import EmotionResult, EmotionStats
from model.emotion.zh import analyze_emotion_zh
from model.emotion.en import analyze_emotion_en

EMOTION_CLASSES = [
    "Joy",
    "Angry",
    "Sad",
    "Surprised",
    "Disgusted",
    "Neutral",
]

def get_main_language(df) -> str:
    counts = df["語言"].value_counts().to_dict()
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
    api = API()
    video_id = api.extract_video_id(url)

    if not video_id:
        return EmotionResult(url=url, error="Invalid YouTube URL")

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
        return EmotionResult(url=url, title=title, error="No comments found")

    df = batch_preprocess_comments(comments)
    if df.empty:
        return EmotionResult(url=url, title=title, error="No valid comments after preprocessing")

    main_lang = get_main_language(df)
    df_lang = df[df["語言"] == main_lang].copy()

    texts = df_lang["清理後留言"].tolist()
    if not texts:
        return EmotionResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            error="No comments for target language"
        )

    # 情緒分類前可先做簡單過濾，避免太短句干擾
    if main_lang == "zh":
        texts = [t for t in texts if len(str(t).strip()) >= 2]
        labels = analyze_emotion_zh(texts)
    elif main_lang == "en":
        texts = [t for t in texts if len(str(t).strip().split()) >= 1]
        labels = analyze_emotion_en(texts)
    else:
        return EmotionResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            error="無法分析此語言"
        )

    if not labels:
        return EmotionResult(
            url=url,
            title=title,
            total_comments=len(df),
            language=main_lang,
            error="No usable comments for emotion analysis"
        )

    counter = Counter(labels)
    emotions = {k: counter.get(k, 0) for k in EMOTION_CLASSES}

    stats = EmotionStats(
        emotions=emotions,
        total=len(labels),
    )

    return EmotionResult(
        url=url,
        title=title,
        total_comments=len(df),
        language=main_lang,
        stats=stats,
    )