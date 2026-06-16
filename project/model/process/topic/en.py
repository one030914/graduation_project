import numpy as np
import pandas as pd
from typing import List

from keybert import KeyBERT

from configs.schema import TopicCluster
from model.process.embedding.loader import get_en_embedder, get_device_str
from model.process.topic.clustering import build_topic_clusterer

def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def build_topics_en(df_lang: pd.DataFrame) -> List[TopicCluster]:
    comments = [
        str(comment).strip()
        for comment in df_lang["clean_text"].tolist()
        if len(str(comment).strip()) >= 6
    ]
    if len(comments) < 2:
        return []

    st_model = get_en_embedder()
    device = get_device_str()
    kw_model = KeyBERT(st_model)

    embeddings = st_model.encode(
        comments,
        device=device,
        batch_size=64,
        show_progress_bar=False,
        normalize_embeddings=True,
    )

    clusterer = build_topic_clusterer(len(comments))
    labels = clusterer.fit_predict(embeddings)

    valid_labels = [lb for lb in set(labels) if lb != -1]
    if not valid_labels:
        return []

    total = sum(1 for lb in labels if lb != -1)
    topics: List[TopicCluster] = []

    for cid in sorted(valid_labels):
        idxs = [i for i, lb in enumerate(labels) if lb == cid]
        cluster_comments = [comments[i] for i in idxs]

        joined = ". ".join(cluster_comments)
        try:
            kws = kw_model.extract_keywords(
                joined,
                keyphrase_ngram_range=(1, 1),
                top_n=8,
                stop_words="english",
                use_mmr=True,
                diversity=0.5,
            )
        except ValueError as exc:
            if "empty vocabulary" not in str(exc).lower():
                raise
            kws = []
        keywords = [
            word
            for word, _ in kws
            if len(word.strip()) >= 3
            and not word.strip().isdigit()
            and len(word.split()) == 1
        ][:5]

        cluster_emb = np.array([embeddings[i] for i in idxs])
        centroid = cluster_emb.mean(axis=0)

        sims = []
        for i in idxs:
            score = _cos_sim(np.array(embeddings[i]), centroid)
            sims.append((comments[i], score))

        sims.sort(key=lambda x: x[1], reverse=True)

        representatives = []
        seen = set()
        for text, _ in sims:
            if text not in seen:
                seen.add(text)
                representatives.append(text)
            if len(representatives) >= 5:
                break

        topics.append(
            TopicCluster(
                cluster_id=int(cid),
                size=len(idxs),
                ratio=len(idxs) / total,
                keywords=keywords,
                representative_comments=representatives,
                language="en"
            )
        )

    topics.sort(key=lambda x: x.size, reverse=True)
    return topics
