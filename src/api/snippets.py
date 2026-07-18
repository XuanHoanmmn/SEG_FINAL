"""Safe accent-insensitive snippets with structured highlight offsets."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class Highlight:
    """One matched term range in the returned snippet text."""

    start: int
    end: int
    term: str


def _fold_character(character: str) -> str:
    replaced = character.replace("đ", "d").replace("Đ", "D")
    decomposed = unicodedata.normalize("NFD", replaced.casefold())
    return "".join(value for value in decomposed if unicodedata.category(value) != "Mn")


def _fold_with_positions(text: str) -> tuple[str, list[int]]:
    folded: list[str] = []
    positions: list[int] = []
    for index, character in enumerate(text):
        for value in _fold_character(character):
            folded.append(value)
            positions.append(index)
    return "".join(folded), positions


def _match_ranges(text: str, terms: tuple[str, ...]) -> list[Highlight]:
    folded_text, positions = _fold_with_positions(text)
    candidates: list[Highlight] = []
    for raw_term in terms:
        display_term = raw_term.replace("_", " ")
        folded_term, _ = _fold_with_positions(display_term)
        if not folded_term:
            continue
        pattern = re.compile(rf"(?<!\w){re.escape(folded_term)}(?!\w)")
        for match in pattern.finditer(folded_text):
            start = positions[match.start()]
            end = positions[match.end() - 1] + 1
            candidates.append(Highlight(start, end, raw_term))

    selected: list[Highlight] = []
    for candidate in sorted(
        candidates,
        key=lambda item: (item.start, -(item.end - item.start), item.term),
    ):
        if any(
            candidate.start < existing.end and candidate.end > existing.start
            for existing in selected
        ):
            continue
        selected.append(candidate)
    return selected


def _field_text(document: dict[str, Any], field: str) -> str:
    value = document.get(field, "")
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    return " ".join(str(value or "").split())


def _window(
    text: str,
    highlights: list[Highlight],
    max_chars: int,
) -> tuple[str, list[Highlight]]:
    if len(text) <= max_chars:
        return text, highlights

    focus = highlights[0].start if highlights else 0
    start = max(0, focus - max_chars // 3)
    end = min(len(text), start + max_chars)
    if end - start < max_chars:
        start = max(0, end - max_chars)
    if start:
        next_space = text.find(" ", start)
        if 0 <= next_space < end:
            start = next_space + 1
    if end < len(text):
        previous_space = text.rfind(" ", start, end)
        if previous_space > start:
            end = previous_space

    prefix = "…" if start else ""
    suffix = "…" if end < len(text) else ""
    snippet_text = prefix + text[start:end] + suffix
    offset = len(prefix) - start
    snippet_highlights = [
        Highlight(item.start + offset, item.end + offset, item.term)
        for item in highlights
        if item.start >= start and item.end <= end
    ]
    return snippet_text, snippet_highlights


def build_snippet(
    document: dict[str, Any],
    matched_fields: tuple[str, ...],
    matched_terms: tuple[str, ...],
    expanded_terms: tuple[str, ...] = (),
    *,
    max_chars: int = 220,
) -> dict[str, Any]:
    """Choose the best matched field and return text plus safe highlight ranges."""

    if max_chars <= 0:
        raise ValueError("max_chars must be positive")
    priority = (
        "title",
        "ingredients",
        "description",
        "instructions",
        "categories",
        "cooking_method",
    )
    fields = [field for field in priority if field in matched_fields]
    fields.extend(field for field in priority if field not in fields)
    terms = tuple(dict.fromkeys((*matched_terms, *expanded_terms)))

    fallback: tuple[str, str] | None = None
    for field in fields:
        text = _field_text(document, field)
        if not text:
            continue
        fallback = fallback or (field, text)
        highlights = _match_ranges(text, terms)
        if not highlights:
            continue
        snippet_text, snippet_highlights = _window(text, highlights, max_chars)
        return {
            "field": field,
            "text": snippet_text,
            "highlights": [asdict(item) for item in snippet_highlights],
        }

    field, text = fallback or ("title", str(document.get("title", "")))
    snippet_text, _ = _window(text, [], max_chars)
    return {"field": field, "text": snippet_text, "highlights": []}
