from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional

import pandas as pd
from keybert import KeyBERT
from sklearn.feature_extraction.text import CountVectorizer

from model.embedding.loader import get_zh_embedder, get_device_str

ZH_VECTORIZER = CountVectorizer(
    tokenizer=lambda s: s.split(),
    preprocessor=None,
    token_pattern=None,
)

st_model = get_zh_embedder()
device = get_device_str()
kw_model = KeyBERT(st_model)

def _dedup_preserve_order(items: List[str], limit: int) -> List[str]:
    seen = set()
    out: List[str] = []
    for x in items:
        x = str(x).strip()
        if not x or x in seen:
            continue
        seen.add(x)
        out.append(x)
        if len(out) >= limit:
            break
    return out

def _build_aligned_docs(
    comments: List[str],
    tokens_zh: Optional[List[List[str]]] = None,
) -> List[str]:
    """
    回傳與 comments 等長的 docs（每筆留言一個 doc）
    優先用 tokens join（"詞 詞 詞"），沒有就退回 comment 本文
    """
    comments = [str(c).strip() for c in (comments or []) if str(c).strip()]
    if not comments:
        return []

    if not tokens_zh:
        return comments

    aligned: List[str] = []
    for i, c in enumerate(comments):
        toks = tokens_zh[i] if i < len(tokens_zh) else None
        if toks is None or (isinstance(toks, float) and pd.isna(toks)):
            aligned.append(c)
            continue
        if isinstance(toks, list):
            toks = [str(w).strip() for w in toks if str(w).strip()]
            aligned.append(" ".join(toks) if toks else c)
        else:
            aligned.append(c)

    return aligned

def _extract_keywords_from_text(
    text: str,
    *,
    top_n: int,
    max_keyword_length: int = 6,
) -> List[str]:
    if not text.strip():
        return []

    kws = KeyBERT(st_model).extract_keywords(
        text,
        top_n=top_n,
        stop_words=None,
        vectorizer=ZH_VECTORIZER,
        keyphrase_ngram_range=(1, 2),
        use_mmr=True,
        diversity=0.5,
    )

    out = []
    for w, _s in kws:
        w = str(w).strip()
        if not w:
            continue
        if max_keyword_length and len(w) > max_keyword_length:
            continue
        out.append(w)
    return out

def extract_cluster_keywords_zh(
    comments: List[str],
    tokens_zh: Optional[List[List[str]]] = None,
    *,
    use_clustering: bool = True,
    min_cluster_size: int = 3,
    per_cluster_topn: int = 5,
    max_keyword_length: int = 6,
    model_folder_name: str = "minilm_chinese_finetuned",
) -> Dict[int, List[str]]:
    comments = [str(c).strip() for c in (comments or []) if str(c).strip()]
    if not comments:
        return {}

    comments = [str(c) if not pd.isna(c) else "" for c in comments]
    comments = [c for c in comments if c]

    st_model = get_zh_embedder(model_folder_name=model_folder_name)
    kw_model = KeyBERT(st_model)

    aligned_docs = _build_aligned_docs(comments, tokens_zh)

    if (not use_clustering) or len(comments) < max(min_cluster_size * 3, 30):
        joined = " ".join(aligned_docs) 
        kws = _extract_keywords_from_text(
            kw_model,
            joined,
            top_n=max(per_cluster_topn, 10),
            max_keyword_length=max_keyword_length,
        )
        return {0: _dedup_preserve_order(kws, per_cluster_topn)}

    try:
        import hdbscan
    except Exception:
        return extract_cluster_keywords_zh(
            comments, tokens_zh,
            use_clustering=False,
            min_cluster_size=min_cluster_size,
            per_cluster_topn=per_cluster_topn,
            max_keyword_length=max_keyword_length,
            model_folder_name=model_folder_name,
        )

    embeddings = st_model.encode(comments, device=device, batch_size=64, show_progress_bar=False)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    clusters: Dict[int, List[int]] = {}
    for idx, lb in enumerate(labels):
        if lb == -1:
            continue
        clusters.setdefault(int(lb), []).append(idx)

    if not clusters:
        return extract_cluster_keywords_zh(
            comments, tokens_zh,
            use_clustering=False,
            min_cluster_size=min_cluster_size,
            per_cluster_topn=per_cluster_topn,
            max_keyword_length=max_keyword_length,
            model_folder_name=model_folder_name,
        )

    result: Dict[int, List[str]] = {}
    for cid, idxs in clusters.items():
        joined = " ".join(aligned_docs[i] for i in idxs if 0 <= i < len(aligned_docs))
        kws = _extract_keywords_from_text(
            kw_model,
            joined,
            top_n=per_cluster_topn,
            max_keyword_length=max_keyword_length,
        )
        result[cid] = _dedup_preserve_order(kws, per_cluster_topn)

    return result

def extract_keywords_zh(
    comments: List[str],
    tokens_zh: Optional[List[List[str]]] = None,
    *,
    topk: int = 12,
    use_clustering: bool = True,
    min_cluster_size: int = 3,
    per_cluster_topn: int = 5,
    max_keyword_length: int = 6,
    model_folder_name: str = "minilm_chinese_finetuned",
) -> List[str]:
    cluster_kw = extract_cluster_keywords_zh(
        comments, tokens_zh,
        use_clustering=use_clustering,
        min_cluster_size=min_cluster_size,
        per_cluster_topn=per_cluster_topn,
        max_keyword_length=max_keyword_length,
        model_folder_name=model_folder_name,
    )

    flat: List[str] = []
    for cid in sorted(cluster_kw.keys()):
        flat.extend(cluster_kw[cid])

    return _dedup_preserve_order(flat, topk)
