from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))

from configs.schema import CommentDataset, TopicCluster
from model.process.topic.clustering import get_min_topic_size
from model.process.topic.en import build_topics_en
from pipeline.topic import build_topics_from_dataset


class _FakeEmbedder:
    def encode(self, comments, **_kwargs):
        return np.array([[float(i), 0.0] for i, _ in enumerate(comments)])


class _FakeClusterer:
    def fit_predict(self, embeddings):
        return np.zeros(len(embeddings), dtype=int)


class _RaisingKeyBERT:
    def __init__(self, *_args, **_kwargs):
        pass

    def extract_keywords(self, *_args, **_kwargs):
        raise ValueError("empty vocabulary; perhaps the documents only contain stop words")


class TopicRegressionTests(unittest.TestCase):
    def test_min_topic_size_does_not_exceed_comment_count(self):
        self.assertEqual(get_min_topic_size(2), 2)

    def test_topic_ratio_uses_all_analyzed_comments_not_only_clustered_comments(self):
        df = pd.DataFrame(
            {
                "language": ["zh"] * 10,
                "clean_text": [f"留言{i}" for i in range(10)],
                "tokens": [["留言", str(i)] for i in range(10)],
                "is_reply": [False] * 10,
                "sample_order": ["relevance"] * 10,
            }
        )
        comments = CommentDataset(
            video_id="test",
            title="test",
            url="https://www.youtube.com/watch?v=test",
            df=df,
        )
        topics = [
            TopicCluster(
                cluster_id=5,
                size=3,
                ratio=1.0,
                keywords=["突破現狀", "小孩子"],
                representative_comments=["突破現狀 / 小孩子"],
                language="zh",
            )
        ]

        with (
            patch("pipeline.topic.build_topics_zh", return_value=topics),
            patch("pipeline.topic.build_topics_en", return_value=[]),
        ):
            result = build_topics_from_dataset(comments)

        self.assertEqual(result.status, "ok")
        self.assertEqual(result.clustered_comments, 3)
        self.assertAlmostEqual(result.coverage_ratio, 0.3)
        self.assertAlmostEqual(result.topics[0].ratio, 0.3)
        self.assertAlmostEqual(result.chart_data[0]["value"], 0.3)

    def test_unsupported_languages_return_error_before_insufficient_data(self):
        df = pd.DataFrame(
            {
                "language": ["unknown"] * 30,
                "clean_text": [f"コメント{i}" for i in range(30)],
                "tokens": [[] for _ in range(30)],
            }
        )
        comments = CommentDataset(
            video_id="test",
            title="test",
            url="https://www.youtube.com/watch?v=test",
            df=df,
        )

        result = build_topics_from_dataset(comments)

        self.assertEqual(result.status, "error")
        self.assertEqual(result.language, "unknown")
        self.assertEqual(result.error, "Cannot analyze this language")

    def test_short_english_comments_are_filtered_before_analyzed_count(self):
        df = pd.DataFrame(
            {
                "language": ["en"] * 8,
                "clean_text": ["why?", "nope", "bad", "yes?", "hmm", "nah", "rip", "wow?"],
                "tokens": [[] for _ in range(8)],
            }
        )
        comments = CommentDataset(
            video_id="test",
            title="test",
            url="https://www.youtube.com/watch?v=test",
            df=df,
        )

        result = build_topics_from_dataset(comments)

        self.assertEqual(result.status, "insufficient_data")
        self.assertEqual(result.language, "en")
        self.assertEqual(result.analyzed_comments, 0)
        self.assertEqual(result.filtered_comments, 8)

    def test_english_empty_vocabulary_keyword_extraction_does_not_crash(self):
        df = pd.DataFrame(
            {
                "clean_text": ["this is the", "and the but", "there was a"],
            }
        )

        with (
            patch("model.process.topic.en.get_en_embedder", return_value=_FakeEmbedder()),
            patch("model.process.topic.en.get_device_str", return_value="cpu"),
            patch("model.process.topic.en.build_topic_clusterer", return_value=_FakeClusterer()),
            patch("model.process.topic.en.KeyBERT", _RaisingKeyBERT),
        ):
            topics = build_topics_en(df)

        self.assertEqual(len(topics), 1)
        self.assertEqual(topics[0].keywords, [])
        self.assertEqual(topics[0].size, 3)


if __name__ == "__main__":
    unittest.main()
