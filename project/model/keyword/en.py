from __future__ import annotations

from functools import lru_cache
from typing import List

import pandas as pd

from configs.settings import MODEL_DIR


@lru_cache(maxsize=1)
def _load_keybert_en(model_folder_name: str = "minilm_english_finetuned"):
    """
    Loads SentenceTransformer + KeyBERT once.
    Expected folder:
      model/minilm_english_finetuned/  (or your actual fine-tuned output)
    """
    from sentence_transformers import SentenceTransformer
    from keybert import KeyBERT

    model_dir = MODEL_DIR / model_folder_name
    st_model = SentenceTransformer(str(model_dir))
    kw_model = KeyBERT(st_model)
    return st_model, kw_model


def extract_keywords_en(
    comments: List[str],
    *,
    topk: int = 10,
    use_clustering: bool = True,
    min_cluster_size: int = 3,
    per_cluster_topn: int = 5,
    model_folder_name: str = "minilm_english_finetuned",
) -> List[str]:
    """
    Input: cleaned English comments
    Output: flattened top keywords list (dedup, in order)

    - If use_clustering=True and enough comments, HDBSCAN -> KeyBERT per cluster
    - Else: KeyBERT on all comments joined
    """
    comments = [str(c).strip() for c in (comments or []) if str(c).strip()]
    if not comments:
        return []

    # handle NaN defensively (in case caller passes from pandas)
    comments = [str(c) if not pd.isna(c) else "" for c in comments]
    comments = [c for c in comments if c]

    st_model, kw_model = _load_keybert_en(model_folder_name=model_folder_name)

    # Small data: no clustering (faster + more stable)
    if (not use_clustering) or len(comments) < max(min_cluster_size * 3, 30):
        joined = ". ".join(comments)
        kws = kw_model.extract_keywords(joined, top_n=max(topk, per_cluster_topn), stop_words="english")
        out = []
        seen = set()
        for w, _score in kws:
            if w and w not in seen:
                seen.add(w)
                out.append(w)
            if len(out) >= topk:
                break
        return out

    # Clustering branch
    try:
        import hdbscan
    except Exception:
        # If hdbscan not installed, fallback
        return extract_keywords_en(
            comments,
            topk=topk,
            use_clustering=False,
            model_folder_name=model_folder_name,
        )

    embeddings = st_model.encode(comments)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    clusters = {}
    for c, lb in zip(comments, labels):
        if lb == -1:
            continue
        clusters.setdefault(int(lb), []).append(c)

    # If all noise, fallback
    if not clusters:
        return extract_keywords_en(
            comments,
            topk=topk,
            use_clustering=False,
            model_folder_name=model_folder_name,
        )

    # Extract per cluster and flatten
    flat: List[str] = []
    for _cid, cmt_list in clusters.items():
        joined = ". ".join(cmt_list)
        kws = kw_model.extract_keywords(joined, top_n=per_cluster_topn, stop_words="english")
        flat.extend([w for w, _ in kws])

    # dedup preserve order
    out = []
    seen = set()
    for w in flat:
        w = str(w).strip()
        if w and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= topk:
            break
    return out
