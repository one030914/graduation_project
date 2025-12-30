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
        raw = entry.get("原留言", "")
        proc = preprocess_comment(raw)

        if not proc.clean_text:
            langs["unknown"] += 1
            continue

        rows.append({
            "語言": proc.language,
            "原留言": proc.raw_text,
            "清理後留言": proc.clean_text,
            "tokens": proc.tokens,
            "按讚數": entry.get("按讚數", 0),
            "回覆數": entry.get("回覆數", 0),
        })
        langs[proc.language] += 1

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["清理後留言"])

    n = sum(langs.values())
    if n > 0:
        ratio = {k: v / n for k, v in langs.items()}
        # 如果你要 pipeline 回傳比例，可改成 return df, ratio
        print(f"語言統計：zh={ratio['zh']:.2%}, en={ratio['en']:.2%}, unknown={ratio['unknown']:.2%}")

    return df
