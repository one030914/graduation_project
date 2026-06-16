from __future__ import annotations

SUPPORTED_JOB_MODES = frozenset(
    {
        "analyze",
        "summary",
        "keyword",
        "topics",
        "emotion",
        "video_content",
        "criticism",
        "timeline",
    }
)

YOUTUBE_REQUIRED_MODES = SUPPORTED_JOB_MODES
OLLAMA_REQUIRED_MODES = frozenset({"analyze", "video_content"})
