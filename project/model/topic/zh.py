from __future__ import annotations

import hdbscan
import numpy as np
from typing import List

from keybert import KeyBERT

from pipeline.schema import TopicCluster
from model.embedding.loader import get_zh_embedder, get_device_str
from model.keyword.zh import kw_model

def _cos_sim(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8))

def build_topics_zh(df_lang) -> List[TopicCluster]:
    comments = df_lang["清理後留言"].tolist()
    tokens_zh = df_lang["tokens"].tolist()
    comments = [c for c in comments if len(c.split()) >= 3]

    st_model = get_zh_embedder()
    device = get_device_str()
    kw_model = KeyBERT(st_model)

    embeddings = st_model.encode(
        comments,
        device=device,
        batch_size=64,
        show_progress_bar=False
    )

    clusterer = hdbscan.HDBSCAN(min_cluster_size=3, min_samples=1, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    valid_labels = [lb for lb in set(labels) if lb != -1]
    if not valid_labels:
        return []

    total = sum(1 for lb in labels if lb != -1)
    topics: List[TopicCluster] = []

    for cid in sorted(valid_labels):
        idxs = [i for i, lb in enumerate(labels) if lb == cid]
        cluster_comments = [comments[i] for i in idxs]
        cluster_tokens = [tokens_zh[i] for i in idxs]

        joined = " ".join(
            " ".join(toks) if isinstance(toks, list) else ""
            for toks in cluster_tokens
        ).strip()

        if not joined:
            joined = " ".join(cluster_comments)

        kws = kw_model.extract_keywords(
            joined,
            top_n=5,
            stop_words=None
        )
        keywords = [w for w, _ in kws][:5]

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
            if len(representatives) >= 2:
                break

        topics.append(
            TopicCluster(
                cluster_id=int(cid),
                size=len(idxs),
                ratio=len(idxs) / total,
                keywords=keywords,
                representative_comments=representatives,
                language="zh"
            )
        )

    topics.sort(key=lambda x: x.size, reverse=True)
    return topics