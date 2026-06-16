from __future__ import annotations

import hdbscan


MIN_TOPIC_SIZE = 3
MAX_TOPIC_SIZE = 20


def get_min_topic_size(comment_count: int) -> int:
    target = max(
        MIN_TOPIC_SIZE,
        min(MAX_TOPIC_SIZE, round(comment_count * 0.01)),
    )
    return min(max(1, comment_count), target)


def build_topic_clusterer(comment_count: int) -> hdbscan.HDBSCAN:
    min_cluster_size = get_min_topic_size(comment_count)

    return hdbscan.HDBSCAN(
        min_cluster_size=min_cluster_size,
        min_samples=1,
        metric="euclidean",
        cluster_selection_method="eom",
        allow_single_cluster=True,
    )
