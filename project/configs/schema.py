"""
Integrate I/O
"""

from __future__ import annotations
import pandas as pd
from datetime import datetime
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field

# ========================================
# Preprocess
# ========================================

@dataclass(slots=True)
class ProcessedComment:
    raw_text: str
    clean_text: str
    language: str
    tokens: List[str]
    timestamps: List[dict]
    urls: List[str]

# ========================================
# Collect
# ========================================

@dataclass(slots=True)
class CommentDataset:
    video_id: str
    title: str
    url: str
    df: pd.DataFrame
    error: Optional[str] = None

# ========================================
# Analysis
# ========================================

@dataclass(slots=True)
class Stats:
    n_comments: int = 0

@dataclass(slots=True)
class LangRatio:
    zh: float = 0.0
    en: float = 0.0
    other: float = 1.0

@dataclass(slots=True)
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

# ========================================
# Video Content
# ========================================

TranscriptSource = Literal["caption", "whisper"]

@dataclass(slots=True)
class VideoContentResult:
    title: str = ""
    url: str = ""
    language: str = ""
    summary_zh: List[str] = field(default_factory=list)
    summary_en: List[str] = field(default_factory=list)
    keywords_zh: List[str] = field(default_factory=list)
    keywords_en: List[str] = field(default_factory=list)
    highlights: List[str] = field(default_factory=list)
    transcript_source: Optional[TranscriptSource] = None
    error: Optional[str] = None

# ========================================
# Queue
# ========================================

@dataclass(slots=True)
class JobStatus:
    status: str  # queued | running | completed | failed | cancelled
    video_id: str
    mode: str
    created_at: datetime
    updated_at: datetime
    expires_at: datetime
    from_cache: Optional[bool] = None
    error: Optional[str] = None
    # 可選：不要讓 web adapter 依賴 queue 內部型別就能序列化結果
    result: Any = None
  
@dataclass
class Job:
    """
    Queue 工作單（不依賴任何 Discord/web 型別）
    """
    job_id: str
    video_id: str
    url: str
    created_at: datetime
    mode: str = "full"
    
class Req(BaseModel):
    video_url: str
    job_mode: str = "full"
    pages: int = 5
    page_size: int = 100
    min_likes: int = 0
    summary_topk: int = 5
    keyword_topk: int = 10
    run_summary: bool = True
    run_keywords: bool = True

# ========================================
# Top Comments
# ========================================

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
    video_id: str = ""
    title: str = ""
    url: str = ""
    top: List[TopComment] = field(default_factory=list)
    total_fetched: int = 0
    order: Order = "relevance"
    sort_by: SortBy = "likes"
    error: Optional[str] = None

# ========================================
# Topics
# ========================================

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

# ========================================   
# Emotion
# ========================================

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

# ========================================
# Video Analysis
# ========================================

class TranscriptChunkAnalysis(BaseModel):
    summary: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)


class TranscriptVideoAnalysis(BaseModel):
    language: str = "unknown"
    summary: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    highlights: List[str] = Field(default_factory=list)
    
@dataclass(slots=True)
class TranscriptSegment:
    text: str
    start: float = 0.0
    duration: float = 0.0

@dataclass(slots=True)
class TranscriptPayload:
    language: str
    source: str
    segments: List[TranscriptSegment]

# ========================================
# Critisism
# ========================================
    
@dataclass(slots=True)
class CommentCriticismResult:
    video_id: str = ""
    title: str = ""
    url: str = ""
    main_criticisms: List[str] = field(default_factory=list)      # 留言中的主要批評與抱怨論點
    discontent_reasons: List[str] = field(default_factory=list)    # 觀眾產生不滿、反彈或質疑的底層原因
    suggestions: List[str] = field(default_factory=list)           # 觀眾給予影片/創作者的改進建議或期望
    error: Optional[str] = None