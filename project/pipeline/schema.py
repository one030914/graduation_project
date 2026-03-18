"""
Integrate I/O
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional, Literal

# Analysis

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
    url: str = ""

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
    mode: str = "full"

# Top Comments

Order = Literal["relevance", "time"]
SortBy = Literal["likes", "replies", "time"]

@dataclass(slots=True)
class TopComment:
    text: str
    like_count: int
    reply_count: int
    published_at: Optional[str] = None
    author: Optional[str] = None
    comment_id: Optional[str] = None

@dataclass(slots=True)
class TopCommentsResult:
    # required fields (no defaults)
    video_id: str
    title: str
    url: str
    top: List[TopComment]
    total_fetched: int
    order: Order
    sort_by: SortBy
    error: Optional[str] = None

# Topics

@dataclass(slots=True)
class TopicCluster:
    cluster_id: int
    size: int
    ratio: float
    keywords: List[str]
    representative_comments: List[str]
    language: Optional[str] = None

@dataclass(slots=True)
class TopicsResult:
    url: str
    title: str = ""
    total_comments: int = 0
    language: str = ""
    topics: List[TopicCluster] = field(default_factory=list)
    error: Optional[str] = None
    
# Emotion

@dataclass(slots=True)
class EmotionStats:
    emotions: Dict[str, int] = field(default_factory=dict)
    total: int = 0

@dataclass(slots=True)
class EmotionResult:
    url: str
    title: str = ""
    total_comments: int = 0
    language: str = ""
    stats: EmotionStats | None = None
    error: Optional[str] = None