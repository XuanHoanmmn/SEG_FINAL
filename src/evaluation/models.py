"""Typed schemas for evaluation queries, judgments and per-query metrics."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.query import SearchFilters


@dataclass(frozen=True, slots=True)
class EvaluationQuery:
    """A stable information need with optional structured filters."""

    query_id: str
    text: str
    intent: str = ""
    filters: SearchFilters = SearchFilters()

    def __post_init__(self) -> None:
        if not self.query_id.strip():
            raise ValueError("query_id cannot be blank")
        if not self.text.strip():
            raise ValueError("query text cannot be blank")

    def to_dict(self) -> dict[str, Any]:
        return {
            "query_id": self.query_id,
            "text": self.text,
            "intent": self.intent,
            "filters": self.filters.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EvaluationQuery:
        filters = dict(data.get("filters") or {})
        return cls(
            query_id=str(data["query_id"]),
            text=str(data["text"]),
            intent=str(data.get("intent", "")),
            filters=SearchFilters(
                max_time_minutes=filters.get("max_time_minutes"),
                difficulty=filters.get("difficulty"),
                categories=tuple(filters.get("categories") or ()),
                ingredients=tuple(filters.get("ingredients") or ()),
                cooking_methods=tuple(filters.get("cooking_methods") or ()),
            ),
        )


@dataclass(frozen=True, slots=True)
class RelevanceJudgment:
    """Human relevance label for one query-document pair."""

    query_id: str
    doc_id: str
    relevance: int

    def __post_init__(self) -> None:
        if not self.query_id.strip() or not self.doc_id.strip():
            raise ValueError("query_id and doc_id cannot be blank")
        if self.relevance not in {0, 1, 2}:
            raise ValueError("relevance must be 0, 1 or 2")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RelevanceJudgment:
        return cls(
            query_id=str(data["query_id"]),
            doc_id=str(data["doc_id"]),
            relevance=int(data["relevance"]),
        )


@dataclass(frozen=True, slots=True)
class QueryMetrics:
    """Standard ranked-retrieval metrics for one evaluated query."""

    precision_at_10: float
    average_precision: float
    recall_at_20: float
    reciprocal_rank_at_10: float
    ndcg_at_10: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)
