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
class VideoChapterSegment:
    start_seconds: int = 0
    end_seconds: int = 0
    title: str = ""
    summary: str = ""
    keywords: List[str] = field(default_factory=list)
    importance: str = "medium"

@dataclass(slots=True)
class VideoContentResult:
    title: str = ""
    url: str = ""
    language: str = ""
    summary_text: str = ""
    final_conclusion: str = ""
    recommended_audience: str = ""
    action_suggestions: List[str] = field(default_factory=list)
    transcript_word_count: int = 0
    chapter_timeline: List[VideoChapterSegment] = field(default_factory=list)
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
    mode: str = "analyze"
    
class Req(BaseModel):
    video_url: str
    job_mode: str = "analyze"
    pages: int = 5
    page_size: int = 100
    min_likes: int = 0
    summary_topk: int = 5
    keyword_topk: int = 10

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

    topic_name: str = ""
    chart_label: str = ""

@dataclass(slots=True)
class TopicsResult:
    url: str
    title: str = ""
    total_comments: int = 0
    analyzed_comments: int = 0
    clustered_comments: int = 0
    noise_count: int = 0
    noise_ratio: float = 0.0
    coverage_ratio: float = 0.0

    language: str = ""
    topics: List[TopicCluster] = field(default_factory=list)

    chart_data: List[Dict[str, Any]] = field(default_factory=list)
    top_keywords: List[str] = field(default_factory=list)

    status: str = "ok"  # ok | insufficient_data | error
    message: Optional[str] = None
    error: Optional[str] = None

# ========================================   
# Emotion
# ========================================

@dataclass(slots=True)
class EmotionStats:
    emotions: Dict[str, int] = field(default_factory=dict)
    ratios: Dict[str, float] = field(default_factory=dict)
    total: int = 0

@dataclass(slots=True)
class EmotionResult:
    url: str
    title: str = ""
    total_comments: int = 0
    analyzed_comments: int = 0
    skipped_comments: int = 0
    language: str = ""

    status: str = "ok"
    message: Optional[str] = None

    stats: EmotionStats | None = None

    emotion_ratios: Dict[str, float] = field(default_factory=dict)

    opinion_score: int = 50
    opinion_label: str = "中性 / 意見分歧"
    positive_ratio: float = 0.0
    negative_ratio: float = 0.0
    neutral_ratio: float = 0.0

    dominant_emotion: Dict[str, Any] = field(default_factory=dict)

    chart_data: List[Dict[str, Any]] = field(default_factory=list)
    radar_data: List[Dict[str, Any]] = field(default_factory=list)

    representative_comments: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)

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
    
# ========================================
# Intent
# ========================================

@dataclass(slots=True)
class IntentComment:
    text: str
    intent: str
    like_count: int = 0
    reply_count: int = 0
    comment_id: str | None = None
    author: str | None = None
    reason: str | None = None
    urls: list[str] = field(default_factory=list)
    timestamps: list[dict] = field(default_factory=list)

@dataclass(slots=True)
class IntentResult:
    video_id: str = ""
    title: str = ""
    url: str = ""

    total_comments: int = 0
    analyzed_comments: int = 0

    status: str = "ok"
    message: str | None = None

    intent_counts: dict[str, int] = field(default_factory=dict)
    intent_ratios: dict[str, float] = field(default_factory=dict)

    actionable_count: int = 0
    actionable_ratio: float = 0.0

    chart_data: list[dict[str, Any]] = field(default_factory=list)

    # 最終給 Discord / analyze 使用
    high_value_actions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    # LLM 原始分類結果，方便 debug
    classified_actions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)

    llm_classified_count: int = 0
    llm_batch_count: int = 0
    llm_ignored_count: int = 0

    questions: list[IntentComment] = field(default_factory=list)
    corrections: list[IntentComment] = field(default_factory=list)
    advice: list[IntentComment] = field(default_factory=list)
    wishlist: list[IntentComment] = field(default_factory=list)
    resources: list[IntentComment] = field(default_factory=list)

    error: str | None = None

# ========================================
# Timeline
# ========================================

@dataclass(slots=True)
class TimelinePoint:
    time_label: str
    seconds: int
    count: int
    ratio: float = 0.0

@dataclass(slots=True)
class TimelineHotspot:
    time_label: str
    seconds: int
    count: int
    representative_comments: list[str] = field(default_factory=list)

@dataclass(slots=True)
class TimelineResult:
    video_id: str = ""
    title: str = ""
    url: str = ""

    total_comments: int = 0

    # 有提及時間戳的「留言數」
    timestamp_comment_count: int = 0
    timestamp_comment_ratio: float = 0.0

    # 時間戳總提及次數，若一則留言提到 2 個時間點，這裡會算 2
    total_timestamp_mentions: int = 0

    bucket_size: int = 30
    peak_count: int = 0

    # 給前端畫完整時間軸曲線
    series: list[TimelinePoint] = field(default_factory=list)

    # 如果前端比較喜歡 dict，也可以直接吃這個
    chart_data: list[dict[str, Any]] = field(default_factory=list)

    hotspots: list[TimelineHotspot] = field(default_factory=list)

    status: str = "ok"  # ok | insufficient_data | error
    message: str | None = None

# ========================================
# Analyze
# ========================================

@dataclass(slots=True)
class AnalyzeResult:
    video_id: str = ""
    title: str = ""
    url: str = ""

    total_comments: int = 0
    public_opinion_score: int = 0
    opinion_label: str = ""

    tags: list[str] = field(default_factory=list)
    quick_summary: list[str] = field(default_factory=list)

    top_topics: list[str] = field(default_factory=list)
    top_hotspot: dict | None = None

    creator_actions: list[str] = field(default_factory=list)
    viewer_tips: list[str] = field(default_factory=list)

    error: str | None = None
