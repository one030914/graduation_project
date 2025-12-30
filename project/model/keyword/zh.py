from __future__ import annotations

from functools import lru_cache
from typing import Dict, List, Optional, Tuple

import pandas as pd

from configs.settings import MODEL_DIR


@lru_cache(maxsize=1)
def _load_keybert_zh(model_folder_name: str = "minilm_chinese_finetuned"):
    """
    Loads SentenceTransformer + KeyBERT once.
    Expected folder:
      model/minilm_chinese_finetuned/  (or your actual fine-tuned output)
    """
    from sentence_transformers import SentenceTransformer
    from keybert import KeyBERT

    model_dir = MODEL_DIR / model_folder_name
    st_model = SentenceTransformer(str(model_dir))
    kw_model = KeyBERT(st_model)
    return st_model, kw_model


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


def _build_docs_for_keywords(
    comments: List[str],
    tokens_zh: Optional[List[List[str]]] = None,
) -> List[str]:
    """
    For Chinese KeyBERT, using token-joined docs often improves phrase stability.
    If tokens_zh is missing/too sparse, fallback to comments.
    """
    comments = [str(c).strip() for c in (comments or []) if str(c).strip()]
    if not comments:
        return []

    if tokens_zh:
        # tokens_zh: list[list[str]] might include None/NaN
        docs = []
        for toks in tokens_zh:
            if toks is None or (isinstance(toks, float) and pd.isna(toks)):
                continue
            if isinstance(toks, list):
                toks = [str(w).strip() for w in toks if str(w).strip()]
                if toks:
                    docs.append(" ".join(toks))
        # 如果 tokens 太少（例如大多數留言沒 tokens），退回用原句
        if len(docs) >= max(10, len(comments) // 5):
            return docs

    return comments


def _extract_keywords_from_text(
    kw_model,
    text: str,
    *,
    top_n: int,
    max_keyword_length: int = 3,
) -> List[str]:
    """
    Runs KeyBERT on a single long text and returns keyword list (filtered).
    """
    if not text.strip():
        return []

    # stop_words 對中文通常不設；你可以之後自訂停用詞再進一步過濾
    kws = kw_model.extract_keywords(text, top_n=top_n, stop_words=None)

    # KeyBERT 回傳 [(kw, score), ...]
    out = []
    for w, _s in kws:
        w = str(w).strip()
        if not w:
            continue
        # 中文常用長度限制
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
    max_keyword_length: int = 3,
    model_folder_name: str = "minilm_chinese_finetuned",
) -> Dict[int, List[str]]:
    """
    Returns cluster_id -> keywords list
    """
    comments = [str(c).strip() for c in (comments or []) if str(c).strip()]
    if not comments:
        return {}

    # 防呆：處理 NaN
    comments = [str(c) if not pd.isna(c) else "" for c in comments]
    comments = [c for c in comments if c]

    st_model, kw_model = _load_keybert_zh(model_folder_name=model_folder_name)

    docs = _build_docs_for_keywords(comments, tokens_zh)

    # 小資料：不分群，整段抽一次，視為 cluster 0
    if (not use_clustering) or len(comments) < max(min_cluster_size * 3, 30):
        joined = "。".join(docs)
        kws = _extract_keywords_from_text(
            kw_model, joined,
            top_n=max(per_cluster_topn, 10),
            max_keyword_length=max_keyword_length
        )
        return {0: _dedup_preserve_order(kws, per_cluster_topn)}

    # 分群需要 hdbscan
    try:
        import hdbscan
    except Exception:
        # 沒裝 hdbscan 就降級
        return extract_cluster_keywords_zh(
            comments, tokens_zh,
            use_clustering=False,
            min_cluster_size=min_cluster_size,
            per_cluster_topn=per_cluster_topn,
            max_keyword_length=max_keyword_length,
            model_folder_name=model_folder_name,
        )

    embeddings = st_model.encode(comments)

    clusterer = hdbscan.HDBSCAN(min_cluster_size=min_cluster_size, metric="euclidean")
    labels = clusterer.fit_predict(embeddings)

    clusters: Dict[int, List[int]] = {}
    for idx, lb in enumerate(labels):
        if lb == -1:
            continue
        clusters.setdefault(int(lb), []).append(idx)

    if not clusters:
        # 全部噪聲就降級
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
        # 用 docs（tokens join）會更穩，但 docs 長度可能和 comments 不一致（tokens sparse）
        # 所以 cluster 內我們用「對應原留言」合併，穩定且不會 index 錯。
        joined = "。".join(comments[i] for i in idxs if 0 <= i < len(comments))

        kws = _extract_keywords_from_text(
            kw_model, joined,
            top_n=per_cluster_topn,
            max_keyword_length=max_keyword_length
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
    max_keyword_length: int = 3,
    model_folder_name: str = "minilm_chinese_finetuned",
) -> List[str]:
    """
    Pipeline-friendly API:
    Input: cleaned zh comments + optional tokens_zh
    Output: flattened keywords list (dedup, preserve order), length <= topk
    """
    cluster_kw = extract_cluster_keywords_zh(
        comments, tokens_zh,
        use_clustering=use_clustering,
        min_cluster_size=min_cluster_size,
        per_cluster_topn=per_cluster_topn,
        max_keyword_length=max_keyword_length,
        model_folder_name=model_folder_name,
    )

    # flatten in cluster_id order (stable)
    flat: List[str] = []
    for cid in sorted(cluster_kw.keys()):
        flat.extend(cluster_kw[cid])

    return _dedup_preserve_order(flat, topk)
