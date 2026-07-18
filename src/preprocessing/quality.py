"""Conservative, auditable cleanup for noisy recipe source fields."""

from __future__ import annotations

from dataclasses import dataclass, replace

from src.models import RecipeDocument
from src.preprocessing.normalizer import normalize_text, strip_accents

INGREDIENT_UI_ARTIFACTS = frozenset({"gram", "muong"})
PROMOTIONAL_DESCRIPTION_PREFIXES = (
    "goi y com nha",
    "goi y bua an",
    "goi y thuc don",
)


@dataclass(frozen=True, slots=True)
class DocumentQualityChanges:
    """Counts of deterministic cleanup operations applied to one document."""

    ingredient_artifacts_removed: int = 0
    promotional_descriptions_cleared: int = 0

    @property
    def changed(self) -> bool:
        return bool(
            self.ingredient_artifacts_removed
            or self.promotional_descriptions_cleared
        )


def _comparison_form(value: str) -> str:
    return strip_accents(normalize_text(value)).strip(" :.-")


def sanitize_recipe_document(
    document: RecipeDocument,
) -> tuple[RecipeDocument, DocumentQualityChanges]:
    """Return a cleaned copy while preserving IDs and source provenance."""

    ingredients = [
        value
        for value in document.ingredients
        if _comparison_form(value) not in INGREDIENT_UI_ARTIFACTS
    ]
    removed_ingredients = len(document.ingredients) - len(ingredients)

    description = document.description
    normalized_description = _comparison_form(description)
    promotional_description = any(
        normalized_description.startswith(prefix)
        for prefix in PROMOTIONAL_DESCRIPTION_PREFIXES
    )
    if promotional_description:
        description = ""

    changes = DocumentQualityChanges(
        ingredient_artifacts_removed=removed_ingredients,
        promotional_descriptions_cleared=int(promotional_description),
    )
    if not changes.changed:
        return document, changes
    return replace(
        document,
        ingredients=ingredients,
        description=description,
    ), changes
