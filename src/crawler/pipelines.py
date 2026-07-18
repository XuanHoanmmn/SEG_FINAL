"""Validation and duplicate prevention for crawled recipe items."""

from __future__ import annotations

from typing import Any

from scrapy.exceptions import DropItem

from src.models import RecipeDocument


class ValidateAndDeduplicatePipeline:
    """Validate the canonical schema and remove URL/content duplicates per run."""

    def __init__(self) -> None:
        self.seen_urls: set[str] = set()
        self.seen_hashes: set[str] = set()

    def process_item(self, item: dict[str, Any], spider: Any) -> dict[str, Any]:
        try:
            document = RecipeDocument.from_dict(dict(item))
        except (TypeError, ValueError) as exc:
            raise DropItem(f"Invalid recipe record: {exc}") from exc

        if document.url in self.seen_urls:
            raise DropItem(f"Duplicate URL: {document.url}")
        if document.content_hash and document.content_hash in self.seen_hashes:
            raise DropItem(f"Duplicate content: {document.url}")

        self.seen_urls.add(document.url)
        if document.content_hash:
            self.seen_hashes.add(document.content_hash)
        return document.to_dict()

