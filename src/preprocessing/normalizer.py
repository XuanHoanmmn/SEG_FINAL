"""Deterministic normalization helpers shared by indexing and querying."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[^\W_]+", flags=re.UNICODE)


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """Normalize Unicode without deleting Vietnamese characters."""

    if form not in {"NFC", "NFD", "NFKC", "NFKD"}:
        raise ValueError(f"Unsupported Unicode normalization form: {form}")
    return unicodedata.normalize(form, text)


def normalize_whitespace(text: str) -> str:
    """Collapse repeated whitespace and trim both ends."""

    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_text(text: str, *, lowercase: bool = True) -> str:
    """Create the canonical accent-preserving form used by the search engine."""

    if not isinstance(text, str):
        raise TypeError("text must be a string")

    result = normalize_unicode(text, "NFC")
    result = normalize_whitespace(result)
    return result.lower() if lowercase else result


def strip_accents(text: str) -> str:
    """Create an accentless Vietnamese form while handling đ/Đ explicitly."""

    decomposed = unicodedata.normalize("NFD", text.replace("đ", "d").replace("Đ", "D"))
    without_marks = "".join(char for char in decomposed if unicodedata.category(char) != "Mn")
    return unicodedata.normalize("NFC", without_marks)


def tokenize_basic(text: str) -> list[str]:
    """Return simple Unicode tokens before Vietnamese word segmentation is applied."""

    return _TOKEN_RE.findall(normalize_text(text))


def build_search_forms(text: str) -> dict[str, str]:
    """Return accent-preserving and accentless forms for indexing or querying."""

    normalized = normalize_text(text)
    return {
        "normalized": normalized,
        "accentless": strip_accents(normalized),
    }

