"""BM25F retrieval with phrase and proximity evidence from positional postings."""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

from src.indexing import PositionalInvertedIndex
from src.preprocessing import INDEXED_FIELDS
from src.query import (
    ProcessedQuery,
    QueryProcessor,
    SearchFilters,
    VietnameseRecipeQueryExpander,
)
from src.retrieval.tfidf import DEFAULT_FIELD_WEIGHTS, SearchResult

DEFAULT_FIELD_B = {
    "title": 0.3,
    "description": 0.75,
    "ingredients": 0.6,
    "instructions": 0.75,
    "categories": 0.3,
    "cooking_method": 0.2,
}


@dataclass(frozen=True, slots=True)
class PhraseEvidence:
    """Phrase/proximity evidence found inside one field of one document."""

    field: str
    exact_phrase_count: int
    minimum_gap: int | None
    bonus: float


class BM25FRetriever:
    """Rank documents with field normalization and positional query boosts."""

    def __init__(
        self,
        index: PositionalInvertedIndex,
        *,
        query_processor: QueryProcessor | None = None,
        field_weights: dict[str, float] | None = None,
        field_b: dict[str, float] | None = None,
        k1: float = 1.2,
        phrase_boost: float = 2.0,
        proximity_boost: float = 1.0,
    ) -> None:
        if k1 <= 0:
            raise ValueError("k1 must be positive")
        if phrase_boost < 0 or proximity_boost < 0:
            raise ValueError("phrase and proximity boosts cannot be negative")

        self.index = index
        self.query_processor = query_processor or QueryProcessor(
            query_expander=VietnameseRecipeQueryExpander()
        )
        self.field_weights = dict(DEFAULT_FIELD_WEIGHTS)
        self.field_b = dict(DEFAULT_FIELD_B)
        if field_weights:
            self.field_weights.update(field_weights)
        if field_b:
            self.field_b.update(field_b)
        if any(weight <= 0 for weight in self.field_weights.values()):
            raise ValueError("field weights must be positive")
        if any(value < 0 or value > 1 for value in self.field_b.values()):
            raise ValueError("field b values must be between 0 and 1")

        self.k1 = k1
        self.phrase_boost = phrase_boost
        self.proximity_boost = proximity_boost
        self.average_field_lengths = self._calculate_average_field_lengths()

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
        numerator = len(self.index) - document_frequency + 0.5
        return math.log(1.0 + numerator / (document_frequency + 0.5))

    def _calculate_average_field_lengths(self) -> dict[str, float]:
        document_count = max(1, len(self.index))
        return {
            field: sum(
                lengths.get(field, 0) for lengths in self.index.document_lengths.values()
            )
            / document_count
            for field in INDEXED_FIELDS
        }

    def _score(
        self,
        query: ProcessedQuery,
        allowed_doc_ids: set[str],
    ) -> list[SearchResult]:
        scores: dict[str, float] = defaultdict(float)
        field_scores: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
        matched_terms: dict[str, set[str]] = defaultdict(set)

        for term, query_frequency in query.term_frequencies.items():
            postings = self.index.get_postings(term, channel=query.channel)
            if not postings:
                continue
            weighted_tf: dict[str, float] = defaultdict(float)
            field_tf: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
            for posting in postings:
                if posting.doc_id not in allowed_doc_ids:
                    continue
                normalized_tf = self._normalized_field_tf(
                    posting.doc_id,
                    posting.field,
                    posting.term_frequency,
                )
                component = self.field_weights.get(posting.field, 1.0) * normalized_tf
                weighted_tf[posting.doc_id] += component
                field_tf[posting.doc_id][posting.field] += component

            idf = self.inverse_document_frequency(term, query.channel)
            query_weight = (1.0 + math.log(query_frequency)) * query.term_boost(term)
            for doc_id, combined_tf in weighted_tf.items():
                term_score = (
                    idf
                    * ((self.k1 + 1.0) * combined_tf)
                    / (self.k1 + combined_tf)
                    * query_weight
                )
                scores[doc_id] += term_score
                matched_terms[doc_id].add(term)
                for field, component in field_tf[doc_id].items():
                    field_scores[doc_id][field] += term_score * component / combined_tf

        if len(query.terms) >= 2:
            self._apply_positional_boosts(
                query,
                scores,
                field_scores,
                allowed_doc_ids,
            )

        return self._build_results(query, scores, field_scores, matched_terms)

    def _normalized_field_tf(self, doc_id: str, field: str, frequency: int) -> float:
        field_length = self.index.document_lengths[doc_id].get(field, 0)
        average_length = self.average_field_lengths.get(field, 0.0) or 1.0
        b_value = self.field_b.get(field, 0.75)
        length_normalization = (1.0 - b_value) + b_value * field_length / average_length
        return frequency / max(length_normalization, 1e-9)

    def _apply_positional_boosts(
        self,
        query: ProcessedQuery,
        scores: dict[str, float],
        field_scores: dict[str, dict[str, float]],
        allowed_doc_ids: set[str],
    ) -> None:
        lookup = self._position_lookup(query)
        for doc_id in set(scores) & allowed_doc_ids:
            for field in INDEXED_FIELDS:
                position_lists = [
                    lookup.get((term, field), {}).get(doc_id, ()) for term in query.terms
                ]
                if any(not positions for positions in position_lists):
                    continue
                evidence = self._phrase_evidence(field, position_lists)
                if evidence.bonus:
                    scores[doc_id] += evidence.bonus
                    field_scores[doc_id][field] += evidence.bonus

    def _position_lookup(
        self,
        query: ProcessedQuery,
    ) -> dict[tuple[str, str], dict[str, tuple[int, ...]]]:
        lookup: dict[tuple[str, str], dict[str, tuple[int, ...]]] = {}
        for term in set(query.terms):
            for field in INDEXED_FIELDS:
                lookup[(term, field)] = {
                    posting.doc_id: posting.positions
                    for posting in self.index.get_postings(
                        term,
                        field=field,
                        channel=query.channel,
                    )
                }
        return lookup

    def _phrase_evidence(
        self,
        field: str,
        position_lists: list[tuple[int, ...]],
    ) -> PhraseEvidence:
        exact_count = _count_exact_phrases(position_lists)
        minimum_gap = _minimum_positional_gap(position_lists)
        field_weight = self.field_weights.get(field, 1.0)
        phrase_bonus = self.phrase_boost * exact_count * field_weight
        proximity_bonus = 0.0
        if minimum_gap is not None:
            proximity_bonus = self.proximity_boost * field_weight / (minimum_gap + 1)
        return PhraseEvidence(
            field=field,
            exact_phrase_count=exact_count,
            minimum_gap=minimum_gap,
            bonus=phrase_bonus + proximity_bonus,
        )

    def _build_results(
        self,
        query: ProcessedQuery,
        scores: dict[str, float],
        field_scores: dict[str, dict[str, float]],
        matched_terms: dict[str, set[str]],
    ) -> list[SearchResult]:
        results: list[SearchResult] = []
        for doc_id, score in scores.items():
            document = self.index.documents[doc_id]
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
                    field_scores=dict(sorted(field_scores[doc_id].items())),
                    expanded_terms=query.expanded_terms,
                )
            )
        return sorted(results, key=lambda item: (-item.score, item.title, item.doc_id))


def _count_exact_phrases(position_lists: list[tuple[int, ...]]) -> int:
    following_positions = [set(positions) for positions in position_lists[1:]]
    return sum(
        1
        for start in position_lists[0]
        if all(
            start + offset in positions
            for offset, positions in enumerate(following_positions, 1)
        )
    )


def _minimum_positional_gap(position_lists: list[tuple[int, ...]]) -> int | None:
    events = sorted(
        (position, term_index)
        for term_index, positions in enumerate(position_lists)
        for position in positions
    )
    counts: dict[int, int] = defaultdict(int)
    covered = 0
    left = 0
    minimum_span: int | None = None
    for right_position, term_index in events:
        if counts[term_index] == 0:
            covered += 1
        counts[term_index] += 1
        while covered == len(position_lists):
            left_position, left_term_index = events[left]
            span = right_position - left_position
            minimum_span = span if minimum_span is None else min(minimum_span, span)
            counts[left_term_index] -= 1
            if counts[left_term_index] == 0:
                covered -= 1
            left += 1
    if minimum_span is None:
        return None
    return max(0, minimum_span - (len(position_lists) - 1))


def _optional_string(value: object) -> str | None:
    return str(value) if value not in (None, "") else None


def _optional_int(value: object) -> int | None:
    return int(value) if value is not None else None
