from model.embedding.loader import get_zh_emotion_model

def analyze_emotion_zh(comments: list[str]) -> list[str]:
    if not comments:
        return []

    pipe = get_zh_emotion_model()
    results = pipe(comments, batch_size=32, truncation=True)

    labels = []
    for r in results:
        raw = str(r["label"]).strip()
        labels.append(raw)

    return labels