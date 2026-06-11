"""
Clean the comments
"""

import re
import unicodedata
import warnings
from dataclasses import dataclass
from typing import Any, List, Tuple

import emoji
import langid
import jieba
import jieba.posseg
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning
from opencc import OpenCC
import contractions
from configs.schema import ProcessedComment

warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

_cct2s = OpenCC("t2s")
_ccs2t = OpenCC("s2t")

PATTERNS = {
    "url": re.compile(r"\b(?:https?://|www\.)\S+\b"),
    "special": re.compile(r"[^0-9A-Za-z\u3400-\u4DBF\u4E00-\u9FFF\u3040-\u309F\u30A0-\u30FF\u2018\u2019\'\s\.,!%?…]"),
    "whitespace": re.compile(r"\s+"),
    "time": re.compile(r"\b\d{1,2}:\d{2}(?::\d{2})?\b"),
    "ellipsis": re.compile(r"(?:…|\.{3,6})"),
    "dup_punc": re.compile(r"([^\w\s])\1+"),
    "repeated": re.compile(r"(?P<grp>.+?)\1+"),
}

CUSTOM_FIXES = {"喫": "吃", "纔": "才", "鬥內": "抖內", "孃": "娘", "穫": "獲", "裏": "裡", "三文治": "三明治", "面": "麵"}
JIEBA_PROTECTED = ["臺灣"]
STOPWORDS = {"是","的","了","有","没","在","也","都","为","能","不","好","像","咧","袂","著","希望","人","听","歌","会","吃","要","看","爱","让","拍","到","说","没有","讲","大","小","首歌","不到"}

def clean_text(text: Any) -> str:
    if not isinstance(text, str):
        return ""
    text = BeautifulSoup(text, "html.parser").get_text()
    text = unicodedata.normalize("NFKC", text)
    text = PATTERNS["url"].sub("", text)
    text = PATTERNS["time"].sub("", text)
    text = emoji.replace_emoji(text, replace="")
    text = PATTERNS["special"].sub("", text)

    ellipses = PATTERNS["ellipsis"].findall(text)
    text = PATTERNS["ellipsis"].sub("<ELLIPSIS>", text)
    text = PATTERNS["dup_punc"].sub(r"\1", text)
    for _ in ellipses:
        text = text.replace("<ELLIPSIS>", "...")

    return PATTERNS["whitespace"].sub(" ", text).strip()

def _zh_char_ratio(s: str) -> float:
    if not s:
        return 0.0
    total = len(s)
    zh = sum(1 for ch in s if "\u4e00" <= ch <= "\u9fff")
    return zh / total if total else 0.0

def _ja_char_ratio(s: str) -> float:
    if not s:
        return 0.0
    total = len(s)
    ja = sum(1 for ch in s if ("\u3040" <= ch <= "\u309F") or ("\u30A0" <= ch <= "\u30FF"))
    return ja / total if total else 0.0

def detect_language(s: str) -> str:
    if _ja_char_ratio(s) >= 0.10:
        return "unknown"
    s = (s or "").strip()
    if not s:
        return "unknown"

    # 中文比例高 → zh
    if _zh_char_ratio(s) >= 0.20:
        return "zh"

    lang = langid.classify(s)[0]

    if lang == "zh":
        return "zh"
    if lang == "en":
        return "en"
    return "unknown"

# ========================================
# Timestamp
# ========================================

TIME_PATTERNS = [
    # 5:10 / 05:10 / 1:02:30 / 1：02：30
    re.compile(r"(?<!\d)(?:\d{1,2}[:：])?\d{1,2}[:：]\d{2}(?!\d)"),

    # 5分10秒 / 05分10秒
    re.compile(r"(?<!\d)(\d{1,2})\s*分\s*(\d{1,2})\s*秒"),

    # 1小時02分30秒
    re.compile(r"(?<!\d)(\d{1,2})\s*小時\s*(\d{1,2})\s*分\s*(\d{1,2})\s*秒"),
]

def timestamp_to_seconds(ts: str) -> int:
    ts = ts.replace("：", ":")

    parts = [int(p) for p in ts.split(":")]

    if len(parts) == 2:
        m, s = parts
        return m * 60 + s

    if len(parts) == 3:
        h, m, s = parts
        return h * 3600 + m * 60 + s

    return 0

def seconds_to_label(seconds: int) -> str:
    seconds = int(seconds)

    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:02d}:{s:02d}"

    return f"{m}:{s:02d}"

def extract_timestamps(text: str) -> list[dict]:
    if not isinstance(text, str):
        return []

    results = []
    occupied_ranges = []

    # 1小時02分30秒
    for match in TIME_PATTERNS[2].finditer(text):
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        total = hours * 3600 + minutes * 60 + seconds

        occupied_ranges.append(match.span())
        results.append({
            "text": match.group(0),
            "seconds": total,
            "label": seconds_to_label(total),
        })

    def overlaps_existing(span: tuple[int, int]) -> bool:
        start, end = span
        return any(start < used_end and used_start < end for used_start, used_end in occupied_ranges)

    # 5:10 / 1:02:30
    for match in TIME_PATTERNS[0].finditer(text):
        if overlaps_existing(match.span()):
            continue

        raw = match.group(0)
        seconds = timestamp_to_seconds(raw)

        occupied_ranges.append(match.span())
        results.append({
            "text": raw,
            "seconds": seconds,
            "label": seconds_to_label(seconds),
        })

    # 5分10秒
    for match in TIME_PATTERNS[1].finditer(text):
        if overlaps_existing(match.span()):
            continue

        minutes = int(match.group(1))
        seconds = int(match.group(2))
        total = minutes * 60 + seconds

        occupied_ranges.append(match.span())
        results.append({
            "text": match.group(0),
            "seconds": total,
            "label": seconds_to_label(total),
        })

    # 去重：同一留言可能同一秒被重複抓到
    seen = set()
    unique = []

    for item in results:
        sec = item["seconds"]
        if sec not in seen:
            seen.add(sec)
            unique.append(item)

    return unique

def extract_urls(text: str) -> list[str]:
    if not isinstance(text, str):
        return []

    return PATTERNS["url"].findall(text)

class TextNormalizer:
    def __init__(self):
        for w in JIEBA_PROTECTED:
            jieba.add_word(w)

    def normalize_chinese(self, text: str) -> Tuple[str, List[str]]:
        simp = _cct2s.convert(text)
        tokens: List[str] = []

        for w, flag in jieba.posseg.lcut(simp):
            w = PATTERNS["repeated"].sub(r"\g<grp>", w)
            if not w or w in STOPWORDS:
                continue
            if flag.startswith(("n", "v", "a")) or flag in ("i", "l"):
                tw = _ccs2t.convert(w)
                tw = CUSTOM_FIXES.get(tw, tw)
                tokens.append(tw)

        tokens = list(dict.fromkeys(tokens))
        cleaned = _ccs2t.convert(simp)  # 保留可讀句子
        return cleaned, tokens

    def normalize_english(self, text: str) -> str:
        text = text.lower()
        text = re.sub(r"([a-z])\1{2,}", r"\1", text)
        return contractions.fix(text)

_NORMALIZER = TextNormalizer()

def preprocess_comment(raw_comment: Any, *, min_len: int = 2) -> ProcessedComment:
    raw = raw_comment if isinstance(raw_comment, str) else ""
    cleaned = clean_text(raw)
    if len(cleaned.strip()) < min_len:
        return ProcessedComment(raw_text=raw, clean_text="", language="unknown", tokens=[], timestamps=[], urls=[])
    lang = detect_language(cleaned)
    tokens: List[str] = []

    if lang == "zh":
        cleaned, tokens = _NORMALIZER.normalize_chinese(cleaned)
    elif lang == "en":
        cleaned = _NORMALIZER.normalize_english(cleaned)

    return ProcessedComment(
        raw_text=raw,
        clean_text=cleaned,
        language=lang,
        tokens=tokens,
        timestamps=extract_timestamps(raw),
        urls=extract_urls(raw),
    )
