"""
Packaging the preprocess pipeline
"""

from typing import Any, Dict, List
import pandas as pd

from .cleaner import preprocess_comment

def batch_preprocess_comments(json_data: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    langs = {"zh": 0, "en": 0, "unknown": 0}

    for entry in json_data:
        raw = entry.get("raw_text", "")
        proc = preprocess_comment(raw)

        if not proc.clean_text:
            langs["unknown"] += 1
            continue

        rows.append({
            "comment_id": entry.get("comment_id"),
            "author": entry.get("author"),
            "language": proc.language,
            "raw_text": proc.raw_text,
            "clean_text": proc.clean_text,
            "tokens": proc.tokens,
            "like_count": entry.get("like_count", 0),
            "reply_count": entry.get("reply_count", 0),
            "published_at": entry.get("published_at"),
            "timestamps": proc.timestamps,
            "urls": proc.urls,
        })
        langs[proc.language] += 1

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["clean_text"])

    n = sum(langs.values())
    if n > 0:
        ratio = {k: v / n for k, v in langs.items()}
        # 如果你要 pipeline 回傳比例，可改成 return df, ratio
        print(f"language statistics: zh={ratio['zh']:.2%}, en={ratio['en']:.2%}, unknown={ratio['unknown']:.2%}")

    return df
