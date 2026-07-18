"""Field-aware positional inverted index implemented for the project."""

from __future__ import annotations

import gzip
import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, TextIO

from src.preprocessing import INDEXED_FIELDS, ProcessedRecipe

INDEX_FORMAT_VERSION = 1
INDEX_CHANNELS = ("normalized", "accentless")


@dataclass(frozen=True, slots=True)
class Posting:
    """One term occurrence list within one document field."""

    doc_id: str
    field: str
    term_frequency: int
    positions: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class IndexStatistics:
    """Compact measurements useful for reports and regression checks."""

    document_count: int
    normalized_vocabulary_size: int
    accentless_vocabulary_size: int
    posting_count: int
    token_count: int

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


class PositionalInvertedIndex:
    """Store term -> field -> document -> token positions for two search forms."""

    def __init__(self) -> None:
        self.documents: dict[str, dict[str, Any]] = {}
        self.document_lengths: dict[str, dict[str, int]] = {}
        self._postings: dict[
            str, dict[str, dict[str, dict[str, list[int]]]]
        ] = {channel: {} for channel in INDEX_CHANNELS}

    def __len__(self) -> int:
        return len(self.documents)

    def add_document(self, recipe: ProcessedRecipe) -> None:
        """Add a processed document and reject duplicate stable IDs."""

        doc_id = recipe.doc_id
        if doc_id in self.documents:
            raise ValueError(f"Duplicate document ID: {doc_id}")

        self.documents[doc_id] = dict(recipe.document)
        self.document_lengths[doc_id] = {
            field: len(recipe.tokens.get(field, [])) for field in INDEXED_FIELDS
        }
        self._add_token_mapping("normalized", doc_id, recipe.tokens)
        self._add_token_mapping("accentless", doc_id, recipe.accentless_tokens)

    def _add_token_mapping(
        self,
        channel: str,
        doc_id: str,
        mapping: dict[str, list[str]],
    ) -> None:
        channel_postings = self._postings[channel]
        for field in INDEXED_FIELDS:
            for position, term in enumerate(mapping.get(field, [])):
                term_fields = channel_postings.setdefault(term, {})
                document_positions = term_fields.setdefault(field, {}).setdefault(doc_id, [])
                document_positions.append(position)

    def terms(self, channel: str = "normalized") -> tuple[str, ...]:
        self._validate_channel(channel)
        return tuple(sorted(self._postings[channel]))

    def get_postings(
        self,
        term: str,
        *,
        field: str | None = None,
        channel: str = "normalized",
    ) -> list[Posting]:
        """Return deterministic postings, optionally restricted to one field."""

        self._validate_channel(channel)
        if field is not None and field not in INDEXED_FIELDS:
            raise ValueError(f"Unknown indexed field: {field}")

        term_fields = self._postings[channel].get(term, {})
        fields = (field,) if field else INDEXED_FIELDS
        result: list[Posting] = []
        for current_field in fields:
            for doc_id, positions in sorted(term_fields.get(current_field, {}).items()):
                result.append(
                    Posting(
                        doc_id=doc_id,
                        field=current_field,
                        term_frequency=len(positions),
                        positions=tuple(positions),
                    )
                )
        return result

    def document_frequency(
        self,
        term: str,
        *,
        field: str | None = None,
        channel: str = "normalized",
    ) -> int:
        postings = self.get_postings(term, field=field, channel=channel)
        return len({posting.doc_id for posting in postings})

    def collection_frequency(
        self,
        term: str,
        *,
        field: str | None = None,
        channel: str = "normalized",
    ) -> int:
        return sum(
            posting.term_frequency
            for posting in self.get_postings(term, field=field, channel=channel)
        )

    def statistics(self) -> IndexStatistics:
        posting_count = sum(
            len(documents)
            for channel in self._postings.values()
            for fields in channel.values()
            for documents in fields.values()
        )
        token_count = sum(sum(lengths.values()) for lengths in self.document_lengths.values())
        return IndexStatistics(
            document_count=len(self),
            normalized_vocabulary_size=len(self._postings["normalized"]),
            accentless_vocabulary_size=len(self._postings["accentless"]),
            posting_count=posting_count,
            token_count=token_count,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "format_version": INDEX_FORMAT_VERSION,
            "indexed_fields": list(INDEXED_FIELDS),
            "documents": self.documents,
            "document_lengths": self.document_lengths,
            "postings": self._postings,
            "statistics": self.statistics().to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PositionalInvertedIndex:
        if data.get("format_version") != INDEX_FORMAT_VERSION:
            raise ValueError("Unsupported inverted-index format version")
        if tuple(data.get("indexed_fields", [])) != INDEXED_FIELDS:
            raise ValueError("Indexed fields do not match this application")

        index = cls()
        index.documents = {
            str(doc_id): dict(document)
            for doc_id, document in dict(data["documents"]).items()
        }
        index.document_lengths = {
            str(doc_id): {str(field): int(length) for field, length in lengths.items()}
            for doc_id, lengths in dict(data["document_lengths"]).items()
        }
        raw_postings = dict(data["postings"])
        for channel in INDEX_CHANNELS:
            index._postings[channel] = {
                str(term): {
                    str(field): {
                        str(doc_id): [int(position) for position in positions]
                        for doc_id, positions in documents.items()
                    }
                    for field, documents in fields.items()
                }
                for term, fields in dict(raw_postings.get(channel, {})).items()
            }
        return index

    def save(self, path: str | Path) -> None:
        """Atomically save deterministic JSON, optionally compressed with gzip."""

        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_suffix(f"{path.suffix}.tmp")
        with _open_text(temporary_path, "wt", compressed=path.suffix == ".gz") as handle:
            json.dump(
                self.to_dict(),
                handle,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        temporary_path.replace(path)

    @classmethod
    def load(cls, path: str | Path) -> PositionalInvertedIndex:
        path = Path(path)
        with _open_text(path, "rt", compressed=path.suffix == ".gz") as handle:
            return cls.from_dict(json.load(handle))

    @staticmethod
    def _validate_channel(channel: str) -> None:
        if channel not in INDEX_CHANNELS:
            raise ValueError(f"Unknown index channel: {channel}")


def _open_text(path: Path, mode: str, *, compressed: bool) -> TextIO:
    if compressed:
        return gzip.open(path, mode, encoding="utf-8")
    return path.open(mode, encoding="utf-8")


def build_inverted_index(recipes: Iterable[ProcessedRecipe]) -> PositionalInvertedIndex:
    """Build an in-memory index from a streaming processed dataset."""

    index = PositionalInvertedIndex()
    for recipe in recipes:
        index.add_document(recipe)
    return index
