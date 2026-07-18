"""Query representation shared by lexical retrieval implementations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from src.preprocessing import VietnameseTextProcessor, normalize_text, strip_accents


@dataclass(frozen=True, slots=True)
class ProcessedQuery:
    """Normalized query terms and the index channel they should search."""

    original: str
    normalized: str
    channel: str
    tokens: tuple[str, ...]
    terms: tuple[str, ...]

    @property
    def term_frequencies(self) -> Counter[str]:
        return Counter(self.terms)


class QueryProcessor:
    """Apply the document tokenizer and choose accent-preserving or accentless search."""

    def __init__(self, text_processor: VietnameseTextProcessor | None = None) -> None:
        self.text_processor = text_processor or VietnameseTextProcessor()

    def process(self, query: str) -> ProcessedQuery:
        normalized = normalize_text(query)
        tokens = self.text_processor.tokenize(normalized)
        ranking_terms = self.text_processor.ranking_terms(tokens)
        if not ranking_terms:
            ranking_terms = tokens

        accentless = strip_accents(normalized)
        channel = "accentless" if normalized == accentless else "normalized"
        terms = (
            [strip_accents(term) for term in ranking_terms]
            if channel == "accentless"
            else ranking_terms
        )
        return ProcessedQuery(
            original=query,
            normalized=normalized,
            channel=channel,
            tokens=tuple(tokens),
            terms=tuple(terms),
        )
