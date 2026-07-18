"""Structured filters shared by lexical retrieval implementations."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from src.preprocessing import normalize_text, strip_accents


@dataclass(frozen=True, slots=True)
class SearchFilters:
    """Optional constraints applied before ranking candidate documents."""

    max_time_minutes: int | None = None
    difficulty: str | None = None
    categories: tuple[str, ...] = ()
    ingredients: tuple[str, ...] = ()
    cooking_methods: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.max_time_minutes is not None and self.max_time_minutes < 0:
            raise ValueError("max_time_minutes cannot be negative")

    @property
    def active(self) -> bool:
        return any(
            (
                self.max_time_minutes is not None,
                self.difficulty,
                self.categories,
                self.ingredients,
                self.cooking_methods,
            )
        )

    def matches(self, document: dict[str, Any]) -> bool:
        if self.max_time_minutes is not None:
            total_time = document.get("total_time_minutes")
            if total_time is None:
                total_time = document.get("cook_time_minutes")
            if total_time is None or int(total_time) > self.max_time_minutes:
                return False

        if self.difficulty and not _same_text(document.get("difficulty"), self.difficulty):
            return False

        document_categories = [str(value) for value in document.get("categories", [])]
        if any(
            not _contains_any(category, document_categories) for category in self.categories
        ):
            return False

        document_ingredients = [str(value) for value in document.get("ingredients", [])]
        if any(
            not _contains_any(ingredient, document_ingredients)
            for ingredient in self.ingredients
        ):
            return False

        if self.cooking_methods and not _contains_any(
            document.get("cooking_method"),
            list(self.cooking_methods),
        ):
            return False
        return True

    def filter_document_ids(self, documents: dict[str, dict[str, Any]]) -> set[str]:
        if not self.active:
            return set(documents)
        return {
            doc_id for doc_id, document in documents.items() if self.matches(document)
        }

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        for field in ("categories", "ingredients", "cooking_methods"):
            value[field] = list(value[field])
        return value


def _search_form(value: object) -> str:
    return strip_accents(normalize_text(str(value or "")))


def _same_text(first: object, second: object) -> bool:
    return _search_form(first) == _search_form(second)


def _contains_any(needle: object, values: list[str]) -> bool:
    normalized_needle = _search_form(needle)
    return bool(normalized_needle) and any(
        normalized_needle in _search_form(value) for value in values
    )
