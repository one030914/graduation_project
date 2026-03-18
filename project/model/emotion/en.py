from model.embedding.loader import get_en_emotion_model

EN_LABEL_MAP = {
    "anger": "Angry",
    "disgust": "Disgusted",
    "fear": "Neutral",
    "joy": "Joy",
    "neutral": "Neutral",
    "sadness": "Sad",
    "surprise": "Surprised",
}

def analyze_emotion_en(comments: list[str]) -> list[str]:
    pipe = get_en_emotion_model()
    results = pipe(comments, batch_size=32, truncation=True)

    labels = []
    for r in results:
        raw = str(r["label"]).strip().lower()
        labels.append(EN_LABEL_MAP.get(raw, "Neutral"))

    return labels