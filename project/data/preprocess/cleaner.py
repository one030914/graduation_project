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

@dataclass
class ProcessedComment:
    raw_text: str
    clean_text: str
    language: str
    tokens: List[str]

def preprocess_comment(raw_comment: Any, *, min_len: int = 2) -> ProcessedComment:
    raw = raw_comment if isinstance(raw_comment, str) else ""
    cleaned = clean_text(raw)

    if len(cleaned.strip()) < min_len:
        return ProcessedComment(raw_text=raw, clean_text="", language="unknown", tokens=[])

    lang = detect_language(cleaned)
    tokens: List[str] = []

    if lang == "zh":
        cleaned, tokens = _NORMALIZER.normalize_chinese(cleaned)
    elif lang == "en":
        cleaned = _NORMALIZER.normalize_english(cleaned)

    return ProcessedComment(raw_text=raw, clean_text=cleaned, language=lang, tokens=tokens)
