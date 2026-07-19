"""Deterministic corpus-profile statistics derived from an index."""

from __future__ import annotations

from collections import Counter
from typing import Any

from src.indexing.inverted_index import PositionalInvertedIndex

PROFILE_FIELDS = (
    "title",
    "description",
    "ingredients",
    "instructions",
    "categories",
    "cooking_method",
    "total_time_minutes",
    "difficulty",
    "image_url",
)


def build_corpus_profile(index: PositionalInvertedIndex) -> dict[str, Any]:
    """Summarize the searchable corpus without relying on generated artifacts."""

    documents = list(index.documents.values())
    document_count = len(documents)
    return {
        "document_count": document_count,
        "sources": _distribution(documents, "source"),
        "categories": _distribution(documents, "categories"),
        "cooking_methods": _distribution(documents, "cooking_method"),
        "difficulties": _distribution(documents, "difficulty"),
        "field_completeness": {
            field: _completeness(documents, field, document_count)
            for field in PROFILE_FIELDS
        },
    }


def _distribution(
    documents: list[dict[str, Any]],
    field: str,
) -> list[dict[str, int | str]]:
    counter: Counter[str] = Counter()
    for document in documents:
        raw_value = document.get(field)
        values = raw_value if isinstance(raw_value, (list, tuple, set)) else (raw_value,)
        for value in values:
            text = str(value).strip() if value not in (None, "") else ""
            if text:
                counter[text] += 1
    return [
        {"value": value, "count": count}
        for value, count in sorted(
            counter.items(),
            key=lambda item: (-item[1], item[0].casefold()),
        )
    ]


def _completeness(
    documents: list[dict[str, Any]],
    field: str,
    document_count: int,
) -> dict[str, int | float]:
    present = sum(1 for document in documents if _has_value(document.get(field)))
    return {
        "present": present,
        "missing": document_count - present,
        "ratio": round(present / document_count, 4) if document_count else 0.0,
    }


def _has_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return bool(value)
    return True
