"""
Integrate I/O
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any

@dataclass
class Stats:
    n_comments: int = 0

@dataclass
class LangRatio:
    zh: float = 0.0
    en: float = 0.0
    other: float = 1.0

@dataclass
class AnalysisResult:
    # video metadata
    video_id: str = ""
    title: str = ""

    # stats
    stats: Stats = field(default_factory=Stats)
    lang_ratio: LangRatio = field(default_factory=LangRatio)

    # outputs (pipeline → embed)
    summary_zh: List[str] = field(default_factory=list)
    summary_en: List[str] = field(default_factory=list)
    keywords_zh: List[str] = field(default_factory=list)
    keywords_en: List[str] = field(default_factory=list)

    # optional debug / future
    comments_zh: List[str] = field(default_factory=list)
    comments_en: List[str] = field(default_factory=list)
    tokens_zh: List[List[str]] = field(default_factory=list)

    # error handling
    error: Optional[str] = None
    
@dataclass
class Job:
    video_id: str
    url: str
    message: discord.Message
    created_at: datetime
    mode: str = "full"   # "full" | "summary" | "keywords"

