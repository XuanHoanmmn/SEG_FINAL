"""Framework-independent search orchestration for the HTTP API."""

from __future__ import annotations

import math
from collections import Counter
from time import perf_counter
from typing import Any

from src.api.snippets import build_snippet
from src.indexing import PositionalInvertedIndex
from src.query import SearchFilters
from src.retrieval import BM25FRetriever, SearchResult, TfidfRetriever


class SearchService:
    """Reuse one loaded index and both rankers across API requests."""

    def __init__(self, index: PositionalInvertedIndex) -> None:
        self.index = index
        self.rankers = {
            "bm25f": BM25FRetriever(index),
            "tfidf": TfidfRetriever(index),
        }

    def search(
        self,
        query: str,
        *,
        ranker_name: str,
        page: int,
        page_size: int,
        filters: SearchFilters,
    ) -> dict[str, Any]:
        started_at = perf_counter()
        ranker = self.rankers[ranker_name]
        processed_query = ranker.query_processor.process(query)
        results = ranker.search(
            query,
            top_k=max(1, len(self.index)),
            filters=filters,
        )
        total = len(results)
        start = (page - 1) * page_size
        page_results = results[start : start + page_size]
        payload = {
            "query": {
                "text": query,
                "normalized": processed_query.normalized,
                "ranker": ranker_name,
                "expanded_terms": list(processed_query.expanded_terms),
                "filters": filters.to_dict(),
            },
            "pagination": {
                "page": page,
                "page_size": page_size,
                "total_results": total,
                "total_pages": math.ceil(total / page_size) if total else 0,
                "has_previous": page > 1,
                "has_next": start + page_size < total,
            },
            "facets": self._facets(results),
            "results": [
                self._serialize_result(result, rank=start + offset)
                for offset, result in enumerate(page_results, start=1)
            ],
        }
        payload["took_ms"] = round((perf_counter() - started_at) * 1000, 3)
        return payload

    def _serialize_result(self, result: SearchResult, *, rank: int) -> dict[str, Any]:
        document = self.index.documents[result.doc_id]
        return {
            "rank": rank,
            "doc_id": result.doc_id,
            "score": round(result.score, 6),
            "title": result.title,
            "url": result.url,
            "source": result.source,
            "image_url": result.image_url,
            "categories": list(result.categories),
            "difficulty": result.difficulty,
            "cook_time_minutes": result.cook_time_minutes,
            "total_time_minutes": document.get("total_time_minutes"),
            "servings": document.get("servings"),
            "snippet": build_snippet(
                document,
                result.matched_fields,
                result.matched_terms,
                result.expanded_terms,
            ),
            "explanation": {
                "matched_terms": list(result.matched_terms),
                "expanded_terms": list(result.expanded_terms),
                "matched_fields": list(result.matched_fields),
                "field_scores": {
                    field: round(score, 6) for field, score in result.field_scores.items()
                },
            },
        }

    def _facets(self, results: list[SearchResult]) -> dict[str, list[dict[str, Any]]]:
        categories: Counter[str] = Counter()
        difficulties: Counter[str] = Counter()
        cooking_methods: Counter[str] = Counter()
        for result in results:
            document = self.index.documents[result.doc_id]
            categories.update(str(value) for value in document.get("categories", []))
            difficulty = document.get("difficulty")
            method = document.get("cooking_method")
            if difficulty:
                difficulties[str(difficulty)] += 1
            if method:
                cooking_methods[str(method)] += 1
        return {
            "categories": _facet_values(categories),
            "difficulties": _facet_values(difficulties),
            "cooking_methods": _facet_values(cooking_methods),
        }


def _facet_values(counter: Counter[str]) -> list[dict[str, Any]]:
    return [
        {"value": value, "count": count}
        for value, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
    ]
