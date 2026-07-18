"""Explainable field-weighted TF-IDF retrieval baseline."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any

from src.indexing import PositionalInvertedIndex
from src.query import ProcessedQuery, QueryProcessor, SearchFilters

DEFAULT_FIELD_WEIGHTS = {
    "title": 3.0,
    "description": 1.0,
    "ingredients": 2.0,
    "instructions": 1.0,
    "categories": 1.5,
    "cooking_method": 1.5,
}


@dataclass(frozen=True, slots=True)
class SearchResult:
    """Ranked document with compact score evidence for debugging and demos."""

    doc_id: str
    score: float
    title: str
    url: str
    source: str
    image_url: str | None
    categories: tuple[str, ...]
    cook_time_minutes: int | None
    difficulty: str | None
    matched_terms: tuple[str, ...]
    matched_fields: tuple[str, ...]
    field_scores: dict[str, float]
    expanded_terms: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["categories"] = list(self.categories)
        value["matched_terms"] = list(self.matched_terms)
        value["matched_fields"] = list(self.matched_fields)
        value["expanded_terms"] = list(self.expanded_terms)
        return value


class TfidfRetriever:
    """Retrieve candidates using log-TF, smoothed IDF and explicit field boosts."""

    def __init__(
        self,
        index: PositionalInvertedIndex,
        *,
        query_processor: QueryProcessor | None = None,
        field_weights: dict[str, float] | None = None,
    ) -> None:
        self.index = index
        self.query_processor = query_processor or QueryProcessor()
        self.field_weights = dict(DEFAULT_FIELD_WEIGHTS)
        if field_weights:
            self.field_weights.update(field_weights)
        self._document_norms = {
            channel: self._calculate_document_norms(channel)
            for channel in ("normalized", "accentless")
        }

    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]:
        if top_k <= 0:
            raise ValueError("top_k must be a positive integer")
        processed_query = self.query_processor.process(query)
        if not processed_query.terms or not self.index.documents:
            return []
        allowed_doc_ids = (filters or SearchFilters()).filter_document_ids(
            self.index.documents
        )
        if not allowed_doc_ids:
            return []
        return self._score(processed_query, allowed_doc_ids)[:top_k]

    def inverse_document_frequency(self, term: str, channel: str) -> float:
        document_frequency = self.index.document_frequency(term, channel=channel)
        return math.log((len(self.index) + 1) / (document_frequency + 1)) + 1.0

    def _calculate_document_norms(self, channel: str) -> dict[str, float]:
        squared_norms: dict[str, float] = defaultdict(float)
        for term in self.index.terms(channel):
            idf = self.inverse_document_frequency(term, channel)
            for posting in self.index.get_postings(term, channel=channel):
                weight = _log_term_frequency(posting.term_frequency) * idf
                squared_norms[posting.doc_id] += weight * weight
        return {
            doc_id: math.sqrt(squared_norms.get(doc_id, 0.0)) or 1.0
            for doc_id in self.index.documents
        }

    def _score(
        self,
        query: ProcessedQuery,
        allowed_doc_ids: set[str],
    ) -> list[SearchResult]:
        query_weights: dict[str, float] = {}
        for term, frequency in query.term_frequencies.items():
            if not self.index.get_postings(term, channel=query.channel):
                continue
            idf = self.inverse_document_frequency(term, query.channel)
            query_weights[term] = (
                _log_term_frequency(frequency) * idf * query.term_boost(term)
            )
        if not query_weights:
            return []

        query_norm = math.sqrt(sum(weight * weight for weight in query_weights.values()))
        scores: dict[str, float] = defaultdict(float)
        field_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        matched_terms: dict[str, set[str]] = defaultdict(set)

        for term, query_weight in query_weights.items():
            idf = self.inverse_document_frequency(term, query.channel)
            for posting in self.index.get_postings(term, channel=query.channel):
                if posting.doc_id not in allowed_doc_ids:
                    continue
                field_weight = self.field_weights.get(posting.field, 1.0)
                document_weight = _log_term_frequency(posting.term_frequency) * idf
                contribution = query_weight * document_weight * field_weight
                scores[posting.doc_id] += contribution
                field_scores[posting.doc_id][posting.field] += contribution
                matched_terms[posting.doc_id].add(term)

        results: list[SearchResult] = []
        for doc_id, dot_product in scores.items():
            denominator = self._document_norms[query.channel][doc_id] * query_norm
            score = dot_product / denominator if denominator else 0.0
            document = self.index.documents[doc_id]
            normalized_field_scores = {
                field: value / denominator
                for field, value in sorted(field_scores[doc_id].items())
            }
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    score=score,
                    title=str(document.get("title", "")),
                    url=str(document.get("url", "")),
                    source=str(document.get("source", "")),
                    image_url=_optional_string(document.get("image_url")),
                    categories=tuple(str(value) for value in document.get("categories", [])),
                    cook_time_minutes=_optional_int(document.get("cook_time_minutes")),
                    difficulty=_optional_string(document.get("difficulty")),
                    matched_terms=tuple(sorted(matched_terms[doc_id])),
                    matched_fields=tuple(sorted(field_scores[doc_id])),
                    field_scores=normalized_field_scores,
                    expanded_terms=query.expanded_terms,
                )
            )

        return sorted(results, key=lambda item: (-item.score, item.title, item.doc_id))


def _log_term_frequency(frequency: int) -> float:
    return 1.0 + math.log(max(1, frequency))


def _optional_string(value: object) -> str | None:
    return str(value) if value not in (None, "") else None


def _optional_int(value: object) -> int | None:
    return int(value) if value is not None else None
