"""Canonical recipe document used across the search pipeline."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(slots=True)
class RecipeDocument:
    """A validated recipe record independent of any source website."""

    doc_id: str
    title: str
    url: str
    source: str
    description: str = ""
    ingredients: list[str] = field(default_factory=list)
    instructions: list[str] = field(default_factory=list)
    categories: list[str] = field(default_factory=list)
    cooking_method: str | None = None
    prep_time_minutes: int | None = None
    cook_time_minutes: int | None = None
    servings: str | None = None
    difficulty: str | None = None
    image_url: str | None = None
    crawled_at: str | None = None
    content_hash: str | None = None

    def __post_init__(self) -> None:
        self.doc_id = str(self.doc_id).strip()
        self.title = self.title.strip()
        self.url = self.url.strip()
        self.source = self.source.strip()

        required = {
            "doc_id": self.doc_id,
            "title": self.title,
            "url": self.url,
            "source": self.source,
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required fields: {', '.join(missing)}")

        for field_name in ("prep_time_minutes", "cook_time_minutes"):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"{field_name} cannot be negative")

    @property
    def total_time_minutes(self) -> int | None:
        """Return total preparation and cooking time when either value exists."""

        values = [self.prep_time_minutes, self.cook_time_minutes]
        if all(value is None for value in values):
            return None
        return sum(value or 0 for value in values)

    def searchable_text(self) -> str:
        """Combine descriptive fields without modifying the original record."""

        parts = [
            self.title,
            self.description,
            " ".join(self.ingredients),
            " ".join(self.instructions),
            " ".join(self.categories),
            self.cooking_method or "",
        ]
        return "\n".join(part for part in parts if part)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the document to a JSON-compatible mapping."""

        result = asdict(self)
        result["total_time_minutes"] = self.total_time_minutes
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RecipeDocument:
        """Create a document while ignoring derived output-only fields."""

        values = dict(data)
        values.pop("total_time_minutes", None)
        return cls(**values)

