from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from configs.schema import TranscriptPayload, TranscriptSegment, VideoChapterSegment
from data.youtube.api import parse_youtube_duration_seconds
from pipeline import video_content


class VideoContentDurationTest(unittest.TestCase):
    def test_parse_youtube_duration_seconds(self):
        self.assertEqual(parse_youtube_duration_seconds("PT13M55S"), 835)
        self.assertEqual(parse_youtube_duration_seconds("PT1H02M03S"), 3723)
        self.assertEqual(parse_youtube_duration_seconds("PT45S"), 45)
        self.assertIsNone(parse_youtube_duration_seconds(""))
        self.assertIsNone(parse_youtube_duration_seconds("not-a-duration"))

    def test_build_video_content_clamps_and_drops_out_of_range_chapters(self):
        transcript = TranscriptPayload(
            language="zh",
            source="caption",
            segments=[
                TranscriptSegment(text="intro text", start=0, duration=10),
                TranscriptSegment(text="ending text", start=830, duration=5),
            ],
        )

        def fake_analyze_transcript_with_llm(**_kwargs):
            return video_content._VideoContentAnalysis(
                language="zh",
                summary_text="summary",
                final_conclusion="conclusion",
                recommended_audience="audience",
                action_suggestions=[],
                chapter_timeline=[
                    VideoChapterSegment(
                        start_seconds=830,
                        end_seconds=860,
                        title="near end",
                        summary="should be clamped",
                    ),
                    VideoChapterSegment(
                        start_seconds=900,
                        end_seconds=930,
                        title="outside",
                        summary="should be dropped",
                    ),
                    VideoChapterSegment(
                        start_seconds=100,
                        end_seconds=100,
                        title="zero",
                        summary="should be dropped",
                    ),
                ],
            )

        original = video_content._analyze_transcript_with_llm
        video_content._analyze_transcript_with_llm = fake_analyze_transcript_with_llm
        try:
            result = video_content.build_video_content_from_transcript(
                transcript,
                title="test",
                url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                video_duration_seconds=835,
            )
        finally:
            video_content._analyze_transcript_with_llm = original

        self.assertIsNone(result.error)
        self.assertEqual(len(result.chapter_timeline), 1)
        self.assertEqual(result.chapter_timeline[0].start_seconds, 830)
        self.assertEqual(result.chapter_timeline[0].end_seconds, 835)

    def test_transcript_lines_include_stable_segment_ids(self):
        lines = video_content._format_transcript_lines(
            [
                TranscriptSegment(text="first", start=0, duration=3),
                TranscriptSegment(text="second", start=3, duration=4),
            ]
        )

        self.assertEqual(lines[0], "[seg=0][00:00 - 00:03] first")
        self.assertEqual(lines[1], "[seg=1][00:03 - 00:07] second")

    def test_segment_ids_override_llm_supplied_seconds(self):
        segments = [
            TranscriptSegment(text="intro", start=0, duration=10),
            TranscriptSegment(text="real start", start=92, duration=8),
            TranscriptSegment(text="real end", start=120, duration=15),
        ]
        data = {
            "language": "zh",
            "summary_text": "summary",
            "chapter_timeline": [
                {
                    "start_segment_id": 1,
                    "end_segment_id": 2,
                    "start_seconds": 999,
                    "end_seconds": 1200,
                    "title": "grounded chapter",
                    "summary": "uses segment times",
                    "keywords": [],
                    "importance": "medium",
                }
            ],
        }

        analysis = video_content._agent_data_to_video_analysis(
            data,
            fallback_language="zh",
            segments=segments,
        )

        self.assertEqual(len(analysis.chapter_timeline), 1)
        self.assertEqual(analysis.chapter_timeline[0].start_seconds, 92)
        self.assertEqual(analysis.chapter_timeline[0].end_seconds, 135)


if __name__ == "__main__":
    unittest.main()
