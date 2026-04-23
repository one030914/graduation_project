from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from data.youtube.transcript import TranscriptPayload, TranscriptSegment, fetch_video_transcript
from pipeline.video_content import TranscriptVideoAnalysis, build_video_content


class FetchVideoTranscriptTests(unittest.TestCase):
    def test_prefers_manual_caption_before_whisper(self):
        transcript = MagicMock()
        transcript.language_code = "en"
        transcript.fetch.return_value = [
            SimpleNamespace(text="hello world", start=0.0, duration=1.0),
        ]

        transcript_list = MagicMock()
        transcript_list.find_manually_created_transcript.return_value = transcript

        api_instance = MagicMock()
        api_instance.list.return_value = transcript_list

        with patch("data.youtube.transcript.YouTubeTranscriptApi", return_value=api_instance), patch(
            "data.youtube.transcript._transcribe_audio"
        ) as whisper_mock:
            result = fetch_video_transcript("https://youtu.be/demo", video_id="demo1234567")

        self.assertEqual(result.source, "caption")
        self.assertEqual(result.language, "en")
        self.assertEqual(len(result.segments), 1)
        whisper_mock.assert_not_called()

    def test_generated_caption_forces_whisper_fallback(self):
        generated_transcript = MagicMock()
        generated_transcript.is_generated = True

        transcript_list = MagicMock()
        transcript_list.find_manually_created_transcript.side_effect = RuntimeError("no manual caption")
        transcript_list.__iter__.return_value = iter([generated_transcript])

        api_instance = MagicMock()
        api_instance.list.return_value = transcript_list
        whisper_result = TranscriptPayload(
            language="en",
            source="whisper",
            segments=[TranscriptSegment(text="fallback transcript")],
        )

        with patch("data.youtube.transcript.YouTubeTranscriptApi", return_value=api_instance), patch(
            "data.youtube.transcript._transcribe_audio", return_value=whisper_result
        ) as whisper_mock:
            result = fetch_video_transcript("https://youtu.be/demo", video_id="demo1234567")

        self.assertEqual(result.source, "whisper")
        self.assertEqual(result.language, "en")
        whisper_mock.assert_called_once()

    def test_falls_back_to_whisper_when_caption_lookup_fails(self):
        api_instance = MagicMock()
        api_instance.list.side_effect = RuntimeError("caption unavailable")
        whisper_result = TranscriptPayload(
            language="en",
            source="whisper",
            segments=[TranscriptSegment(text="fallback transcript")],
        )

        with patch("data.youtube.transcript.YouTubeTranscriptApi", return_value=api_instance), patch(
            "data.youtube.transcript._transcribe_audio", return_value=whisper_result
        ) as whisper_mock:
            result = fetch_video_transcript("https://youtu.be/demo", video_id="demo1234567")

        self.assertEqual(result.source, "whisper")
        self.assertEqual(result.language, "en")
        whisper_mock.assert_called_once()


class BuildVideoContentTests(unittest.TestCase):
    def test_builds_english_video_content_result(self):
        api_instance = MagicMock()
        api_instance.extract_video_id.return_value = "demo1234567"
        api_instance.get_video_info.return_value = {"title": "Demo video"}

        transcript = TranscriptPayload(
            language="en",
            source="whisper",
            segments=[
                TranscriptSegment(text="This feature saves a lot of time for users."),
                TranscriptSegment(text="The interface is simple and easy to use."),
            ],
        )
        llm_output = TranscriptVideoAnalysis(
            language="en",
            summary=["The video explains a time-saving feature."],
            keywords=["time-saving feature", "simple interface"],
            highlights=["This feature saves a lot of time for users."],
        )

        with patch("pipeline.video_content.API", return_value=api_instance), patch(
            "pipeline.video_content.fetch_video_transcript", return_value=transcript
        ), patch("pipeline.video_content._analyze_transcript_with_llm", return_value=llm_output):
            result = build_video_content("https://youtu.be/demo")

        self.assertEqual(result.title, "Demo video")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.transcript_source, "whisper")
        self.assertEqual(result.summary_en, ["The video explains a time-saving feature."])
        self.assertEqual(result.keywords_en, ["time-saving feature", "simple interface"])
        self.assertEqual(result.highlights, ["This feature saves a lot of time for users."])

    def test_builds_chinese_video_content_result(self):
        api_instance = MagicMock()
        api_instance.extract_video_id.return_value = "demo1234567"
        api_instance.get_video_info.return_value = {"title": "示範影片"}

        transcript = TranscriptPayload(
            language="zh-TW",
            source="caption",
            segments=[
                TranscriptSegment(text="這支影片介紹如何快速整理會議逐字稿。"),
                TranscriptSegment(text="也說明了如何從逐字稿提取摘要與關鍵字。"),
            ],
        )
        llm_output = TranscriptVideoAnalysis(
            language="zh",
            summary=["影片介紹如何整理逐字稿並提取重點。"],
            keywords=["逐字稿", "摘要", "關鍵字"],
            highlights=["也說明了如何從逐字稿提取摘要與關鍵字。"],
        )

        with patch("pipeline.video_content.API", return_value=api_instance), patch(
            "pipeline.video_content.fetch_video_transcript", return_value=transcript
        ), patch("pipeline.video_content._analyze_transcript_with_llm", return_value=llm_output):
            result = build_video_content("https://youtu.be/demo")

        self.assertEqual(result.title, "示範影片")
        self.assertEqual(result.language, "zh")
        self.assertEqual(result.summary_zh, ["影片介紹如何整理逐字稿並提取重點。"])
        self.assertEqual(result.keywords_zh, ["逐字稿", "摘要", "關鍵字"])
        self.assertEqual(result.highlights, ["也說明了如何從逐字稿提取摘要與關鍵字。"])


if __name__ == "__main__":
    unittest.main()
