from .collect import collect_comments
from configs.schema import AnalysisResult, Stats, LangRatio
from scripts.timestamp import Timer

def analyze(video_url: str, *, pages: int = 100, page_size: int = 100, min_likes: int = 0,
            summary_topk: int = 5, keyword_topk: int = 10, run_summary: bool = True, run_keywords: bool = True) -> AnalysisResult:
    timer = Timer()
    
    comments = collect_comments(url=video_url, pages=pages, page_size=page_size, min_likes=min_likes)
    
    if comments.error:
        return AnalysisResult(error=comments.error)
    
    timer.mark("api fetch")
    
    df = comments.df.copy()

    comments_zh = df[df["language"] == "zh"]["clean_text"].tolist()
    comments_en = df[df["language"] == "en"]["clean_text"].tolist()
    tokens_zh = df[df["language"] == "zh"]["tokens"].tolist()
    lang_counts = df["language"].value_counts(dropna=False).to_dict()
    zh = float(lang_counts.get("zh", 0) / len(df))
    en = float(lang_counts.get("en", 0) / len(df))
    other = max(0.0, 1.0 - zh - en)

    MAX_N = 600
    comments_zh = comments_zh[:MAX_N]
    tokens_zh = tokens_zh[:MAX_N]
    comments_en = comments_en[:MAX_N]
    
    timer.mark("split language")

    summary_zh = comments_zh[:summary_topk]
    summary_en = comments_en[:summary_topk]
    keywords_zh = []
    keywords_en = []

    # -------------------------
    # Summary
    # -------------------------
    if run_summary:
        try:
            from model.process.summary.zh import summarize_zh
            summary_zh = summarize_zh(comments_zh, topk=summary_topk)
        except Exception as e:
            print("Error: summarize zh", e)
            
        timer.mark("summarize zh")

        try:
            from model.process.summary.en import summarize_en
            summary_en = summarize_en(comments_en, topk=summary_topk)
        except Exception as e:
            print("Error: summarize en", e)

        timer.mark("summarize en")

    # -------------------------
    # Keywords
    # -------------------------
    if run_keywords:
        try:
            from model.process.keyword.zh import extract_keywords_zh
            keywords_zh = extract_keywords_zh(comments_zh, tokens_zh, topk=keyword_topk)
        except Exception:
            # fallback：tokens 攤平 + 去重保序
            flat = [w for toks in tokens_zh for w in (toks or [])]
            seen = set()
            for w in flat:
                w = str(w).strip()
                if w and w not in seen:
                    seen.add(w)
                    keywords_zh.append(w)
                if len(keywords_zh) >= keyword_topk:
                    break
                
        timer.mark("extract keywords zh")

        try:
            from model.process.keyword.en import extract_keywords_en
            keywords_en = extract_keywords_en(comments_en, topk=keyword_topk)
        except Exception:
            keywords_en = []

        timer.mark("extract keywords en")

    result = AnalysisResult(
        video_id=comments.video_id,
        title=comments.title,
        url=comments.url,
        stats=Stats(n_comments=len(df)),
        lang_ratio=LangRatio(zh=zh, en=en, other=other),
        comments_zh=comments_zh[:MAX_N],
        comments_en=comments_en[:MAX_N],
        tokens_zh=tokens_zh[:MAX_N],
        summary_zh=summary_zh[:summary_topk],
        summary_en=summary_en[:summary_topk],
        keywords_zh=keywords_zh[:keyword_topk],
        keywords_en=keywords_en[:keyword_topk],
    )
    return result