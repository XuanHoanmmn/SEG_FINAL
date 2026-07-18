"""Small transparent synonym map for Vietnamese recipe-domain concepts."""

from __future__ import annotations

from src.preprocessing import normalize_text, strip_accents

DEFAULT_RECIPE_EXPANSIONS = {
    "hai san": ("cá", "tôm", "mực", "nghêu", "ốc"),
}


class VietnameseRecipeQueryExpander:
    """Expand only explicit domain concepts with reviewable deterministic terms."""

    def __init__(
        self,
        expansions: dict[str, tuple[str, ...]] | None = None,
    ) -> None:
        values = expansions or DEFAULT_RECIPE_EXPANSIONS
        self.expansions = {
            strip_accents(normalize_text(concept)): tuple(terms)
            for concept, terms in values.items()
        }

    def expand(self, query: str) -> tuple[str, ...]:
        normalized_query = strip_accents(normalize_text(query))
        padded_query = f" {normalized_query} "
        expanded: list[str] = []
        for concept, terms in self.expansions.items():
            if f" {concept} " not in padded_query:
                continue
            for term in terms:
                if term not in expanded:
                    expanded.append(term)
        return tuple(expanded)
