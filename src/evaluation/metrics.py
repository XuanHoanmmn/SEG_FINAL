"""Dependency-free information-retrieval metrics used by offline experiments."""

from __future__ import annotations

import math
from collections.abc import Iterable, Sequence

from src.evaluation.models import QueryMetrics


def precision_at_k(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    _validate_k(k)
    relevant_hits = sum(relevance.get(doc_id, 0) > 0 for doc_id in ranked_doc_ids[:k])
    return relevant_hits / k


def average_precision(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
) -> float:
    relevant_count = sum(value > 0 for value in relevance.values())
    if relevant_count == 0:
        return 0.0
    hits = 0
    precision_sum = 0.0
    for rank, doc_id in enumerate(ranked_doc_ids, start=1):
        if relevance.get(doc_id, 0) > 0:
            hits += 1
            precision_sum += hits / rank
    return precision_sum / relevant_count


def recall_at_k(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    _validate_k(k)
    relevant_count = sum(value > 0 for value in relevance.values())
    if relevant_count == 0:
        return 0.0
    hits = sum(relevance.get(doc_id, 0) > 0 for doc_id in ranked_doc_ids[:k])
    return hits / relevant_count


def reciprocal_rank_at_k(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    _validate_k(k)
    for rank, doc_id in enumerate(ranked_doc_ids[:k], start=1):
        if relevance.get(doc_id, 0) > 0:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
    k: int,
) -> float:
    _validate_k(k)
    gains = [relevance.get(doc_id, 0) for doc_id in ranked_doc_ids[:k]]
    actual = _discounted_cumulative_gain(gains)
    ideal_gains = sorted(relevance.values(), reverse=True)[:k]
    ideal = _discounted_cumulative_gain(ideal_gains)
    return actual / ideal if ideal else 0.0


def evaluate_ranking(
    ranked_doc_ids: Sequence[str],
    relevance: dict[str, int],
) -> QueryMetrics:
    return QueryMetrics(
        precision_at_10=precision_at_k(ranked_doc_ids, relevance, 10),
        average_precision=average_precision(ranked_doc_ids, relevance),
        recall_at_20=recall_at_k(ranked_doc_ids, relevance, 20),
        reciprocal_rank_at_10=reciprocal_rank_at_k(ranked_doc_ids, relevance, 10),
        ndcg_at_10=ndcg_at_k(ranked_doc_ids, relevance, 10),
    )


def mean_metrics(metrics: Iterable[QueryMetrics]) -> QueryMetrics:
    values = list(metrics)
    if not values:
        return QueryMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
    count = len(values)
    return QueryMetrics(
        precision_at_10=sum(item.precision_at_10 for item in values) / count,
        average_precision=sum(item.average_precision for item in values) / count,
        recall_at_20=sum(item.recall_at_20 for item in values) / count,
        reciprocal_rank_at_10=sum(item.reciprocal_rank_at_10 for item in values) / count,
        ndcg_at_10=sum(item.ndcg_at_10 for item in values) / count,
    )


def percentile(values: Sequence[float], percentage: float) -> float:
    if not values:
        return 0.0
    if percentage < 0 or percentage > 100:
        raise ValueError("percentage must be between 0 and 100")
    ordered = sorted(values)
    position = (len(ordered) - 1) * percentage / 100
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def _discounted_cumulative_gain(gains: Sequence[int]) -> float:
    return sum((2**gain - 1) / math.log2(rank + 1) for rank, gain in enumerate(gains, 1))


def _validate_k(k: int) -> None:
    if k <= 0:
        raise ValueError("k must be positive")
