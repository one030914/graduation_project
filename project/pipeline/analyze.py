from data.youtube.api import API
from data.preprocess.pipeline import batch_preprocess_comments
from pipeline.schema import AnalysisResult, Stats, LangRatio
from scripts.timestamp import Timer

def analyze(video_url: str, *, pages: int = 5, page_size: int = 100, min_likes: int = 0,
            summary_topk: int = 5, keyword_topk: int = 10, run_summary: bool = True, run_keywords: bool = True) -> AnalysisResult:
    timer = Timer()
    
    api = API()
    
    video_id = api.extract_video_id(video_url)
    if not video_id:
        return AnalysisResult(error="Invalid YouTube URL / video_id not found.")

    video_info = api.get_video_info(video_id)
    title = (video_info or {}).get("title") or video_id

    comments = api.get_comments(url=video_url, page_size=page_size, pages=pages, min_likes=min_likes)
    
    if len(comments) < 100:
        return AnalysisResult(
            video_id=video_id,
            title=title,
            url=video_url,
            stats=Stats(n_comments=0),
            lang_ratio=LangRatio(zh=0.0, en=0.0, other=1.0),
            error="留言數不足以分析"
        )
    
    timer.mark("api fetch")
    
    df = batch_preprocess_comments(comments)
    
    timer.mark("preprocess")

    if df.empty:
        return AnalysisResult(
            video_id=video_id,
            title=title,
            url=video_url,
            stats=Stats(n_comments=0),
            lang_ratio=LangRatio(zh=0.0, en=0.0, other=1.0),
        )

    lang_counts = df["語言"].value_counts(dropna=False).to_dict()
    n = int(len(df))
    zh = float(lang_counts.get("zh", 0) / n)
    en = float(lang_counts.get("en", 0) / n)
    other = max(0.0, 1.0 - zh - en)

    comments_zh = df[df["語言"] == "zh"]["清理後留言"].tolist()
    comments_en = df[df["語言"] == "en"]["清理後留言"].tolist()
    tokens_zh = df[df["語言"] == "zh"]["tokens"].tolist()

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
            from model.summary.zh import summarize_zh
            summary_zh = summarize_zh(comments_zh, topk=summary_topk)
        except Exception as e:
            print("Error: summarize zh", e)
            
        timer.mark("summarize zh")

        try:
            from model.summary.en import summarize_en
            summary_en = summarize_en(comments_en, topk=summary_topk)
        except Exception as e:
            print("Error: summarize en", e)

        timer.mark("summarize en")

    # -------------------------
    # Keywords
    # -------------------------
    if run_keywords:
        try:
            from model.keyword.zh import extract_keywords_zh
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
            from model.keyword.en import extract_keywords_en
            keywords_en = extract_keywords_en(comments_en, topk=keyword_topk)
        except Exception:
            keywords_en = []

        timer.mark("extract keywords en")

    result = AnalysisResult(
        video_id=video_id,
        title=title,
        url=video_url,
        stats=Stats(n_comments=n),
        lang_ratio=LangRatio(zh=zh, en=en, other=other),
        comments_zh=comments_zh,
        comments_en=comments_en,
        tokens_zh=tokens_zh,
        summary_zh=summary_zh,
        summary_en=summary_en,
        keywords_zh=keywords_zh,
        keywords_en=keywords_en,
    )

    print(timer.report())
    return result