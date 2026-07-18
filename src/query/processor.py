"""Query representation shared by lexical retrieval implementations."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Protocol

from src.preprocessing import VietnameseTextProcessor, normalize_text, strip_accents


@dataclass(frozen=True, slots=True)
class ProcessedQuery:
    """Normalized query terms and the index channel they should search."""

    original: str
    normalized: str
    channel: str
    tokens: tuple[str, ...]
    terms: tuple[str, ...]
    expanded_terms: tuple[str, ...] = ()
    expansion_boost: float = 0.35

    @property
    def term_frequencies(self) -> Counter[str]:
        return Counter((*self.terms, *self.expanded_terms))

    def term_boost(self, term: str) -> float:
        """Keep original terms dominant over automatically expanded terms."""

        return 1.0 if term in self.terms else self.expansion_boost


class QueryExpander(Protocol):
    def expand(self, query: str) -> tuple[str, ...]: ...


class QueryProcessor:
    """Apply the document tokenizer and choose accent-preserving or accentless search."""

    def __init__(
        self,
        text_processor: VietnameseTextProcessor | None = None,
        *,
        query_expander: QueryExpander | None = None,
        expansion_boost: float = 0.35,
    ) -> None:
        if expansion_boost <= 0 or expansion_boost > 1:
            raise ValueError("expansion_boost must be in (0, 1]")
        self.text_processor = text_processor or VietnameseTextProcessor()
        self.query_expander = query_expander
        self.expansion_boost = expansion_boost

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
        expanded_terms: list[str] = []
        if self.query_expander is not None:
            for value in self.query_expander.expand(normalized):
                expansion_tokens = self.text_processor.ranking_terms(
                    self.text_processor.tokenize(value)
                )
                if not expansion_tokens:
                    expansion_tokens = self.text_processor.tokenize(value)
                if channel == "accentless":
                    expansion_tokens = [strip_accents(term) for term in expansion_tokens]
                for term in expansion_tokens:
                    if term not in terms and term not in expanded_terms:
                        expanded_terms.append(term)
        return ProcessedQuery(
            original=query,
            normalized=normalized,
            channel=channel,
            tokens=tuple(tokens),
            terms=tuple(terms),
            expanded_terms=tuple(expanded_terms),
            expansion_boost=self.expansion_boost,
        )
