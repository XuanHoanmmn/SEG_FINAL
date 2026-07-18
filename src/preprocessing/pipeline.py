"""Reproducible preprocessing for raw Vietnamese recipe documents."""

from __future__ import annotations

import json
from collections.abc import Callable, Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.models import RecipeDocument
from src.preprocessing.normalizer import normalize_text, strip_accents, tokenize_basic
from src.preprocessing.quality import sanitize_recipe_document

INDEXED_FIELDS = (
    "title",
    "description",
    "ingredients",
    "instructions",
    "categories",
    "cooking_method",
)

DEFAULT_VIETNAMESE_STOPWORDS = frozenset(
    {
        "bị",
        "bởi",
        "các",
        "cho",
        "có",
        "của",
        "cùng",
        "đã",
        "đang",
        "để",
        "đến",
        "được",
        "khi",
        "là",
        "lại",
        "làm",
        "một",
        "những",
        "này",
        "nên",
        "ra",
        "rồi",
        "sau",
        "sẽ",
        "theo",
        "thì",
        "trên",
        "trong",
        "từ",
        "và",
        "vào",
        "với",
    }
)

Segmenter = Callable[[str], Iterable[str] | str]


@dataclass(slots=True)
class ProcessedRecipe:
    """Original recipe plus normalized field-level search representations."""

    document: dict[str, Any]
    normalized_fields: dict[str, str]
    tokens: dict[str, list[str]]
    accentless_tokens: dict[str, list[str]]
    ranking_tokens: dict[str, list[str]]

    @property
    def doc_id(self) -> str:
        return str(self.document["doc_id"])

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProcessedRecipe:
        return cls(
            document=dict(data["document"]),
            normalized_fields={
                str(field): str(value)
                for field, value in dict(data["normalized_fields"]).items()
            },
            tokens=_token_mapping(data["tokens"]),
            accentless_tokens=_token_mapping(data["accentless_tokens"]),
            ranking_tokens=_token_mapping(data["ranking_tokens"]),
        )


@dataclass(slots=True)
class ProcessingReport:
    """Quality counters emitted while transforming a raw JSONL dataset."""

    input_records: int = 0
    output_records: int = 0
    duplicate_records: int = 0
    invalid_records: int = 0
    cleaned_records: int = 0
    ingredient_artifacts_removed: int = 0
    promotional_descriptions_cleared: int = 0

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def _token_mapping(value: object) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        raise TypeError("token mapping must be an object")
    return {
        str(field): [str(token) for token in tokens]
        for field, tokens in value.items()
    }


def _load_underthesea_segmenter() -> Segmenter | None:
    try:
        from underthesea import word_tokenize
    except ImportError:
        return None

    def segment(text: str) -> str:
        return str(word_tokenize(text, format="text"))

    return segment


class VietnameseTextProcessor:
    """Apply identical Vietnamese normalization to documents and future queries."""

    def __init__(
        self,
        *,
        use_word_segmentation: bool = True,
        segmenter: Segmenter | None = None,
        stopwords: Iterable[str] = DEFAULT_VIETNAMESE_STOPWORDS,
    ) -> None:
        self.segmenter = segmenter
        if self.segmenter is None and use_word_segmentation:
            self.segmenter = _load_underthesea_segmenter()
        self.stopwords = {normalize_text(word) for word in stopwords}

    def tokenize(self, text: str) -> list[str]:
        normalized = normalize_text(text)
        if not normalized:
            return []
        if self.segmenter is None:
            return tokenize_basic(normalized)

        segmented = self.segmenter(normalized)
        values = segmented.split() if isinstance(segmented, str) else list(segmented)
        result: list[str] = []
        for value in values:
            token = normalize_text(str(value)).replace(" ", "_")
            if token:
                result.append(token)
        return result

    def ranking_terms(self, tokens: Iterable[str]) -> list[str]:
        return [
            token
            for token in tokens
            if token not in self.stopwords and strip_accents(token) not in self.stopwords
        ]


def _field_texts(document: RecipeDocument) -> dict[str, str]:
    return {
        "title": document.title,
        "description": document.description,
        "ingredients": "\n".join(document.ingredients),
        "instructions": "\n".join(document.instructions),
        "categories": "\n".join(document.categories),
        "cooking_method": document.cooking_method or "",
    }


def process_document(
    document: RecipeDocument,
    processor: VietnameseTextProcessor | None = None,
) -> ProcessedRecipe:
    """Preserve source fields while producing normalized positional token streams."""

    processor = processor or VietnameseTextProcessor()
    normalized_fields: dict[str, str] = {}
    tokens: dict[str, list[str]] = {}
    accentless_tokens: dict[str, list[str]] = {}
    ranking_tokens: dict[str, list[str]] = {}

    for field, text in _field_texts(document).items():
        normalized_fields[field] = normalize_text(text)
        field_tokens = processor.tokenize(text)
        tokens[field] = field_tokens
        accentless_tokens[field] = [strip_accents(token) for token in field_tokens]
        ranking_tokens[field] = processor.ranking_terms(field_tokens)

    return ProcessedRecipe(
        document=document.to_dict(),
        normalized_fields=normalized_fields,
        tokens=tokens,
        accentless_tokens=accentless_tokens,
        ranking_tokens=ranking_tokens,
    )


def iter_processed_jsonl(path: str | Path) -> Iterable[ProcessedRecipe]:
    """Stream validated processed records without loading the dataset at once."""

    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                yield ProcessedRecipe.from_dict(json.loads(line))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid processed JSONL at line {line_number}") from exc


def process_jsonl(
    input_path: str | Path,
    output_path: str | Path,
    processor: VietnameseTextProcessor | None = None,
) -> ProcessingReport:
    """Validate, deduplicate and atomically write a processed recipe JSONL file."""

    processor = processor or VietnameseTextProcessor()
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(f"{output_path.suffix}.tmp")
    report = ProcessingReport()
    seen_ids: set[str] = set()
    seen_hashes: set[str] = set()

    with input_path.open(encoding="utf-8") as source, temporary_path.open(
        "w", encoding="utf-8", newline="\n"
    ) as target:
        for line in source:
            if not line.strip():
                continue
            report.input_records += 1
            try:
                document = RecipeDocument.from_dict(json.loads(line))
            except (TypeError, ValueError, json.JSONDecodeError):
                report.invalid_records += 1
                continue

            duplicate_hash = document.content_hash and document.content_hash in seen_hashes
            if document.doc_id in seen_ids or duplicate_hash:
                report.duplicate_records += 1
                continue

            seen_ids.add(document.doc_id)
            if document.content_hash:
                seen_hashes.add(document.content_hash)
            document, quality_changes = sanitize_recipe_document(document)
            if quality_changes.changed:
                report.cleaned_records += 1
            report.ingredient_artifacts_removed += (
                quality_changes.ingredient_artifacts_removed
            )
            report.promotional_descriptions_cleared += (
                quality_changes.promotional_descriptions_cleared
            )
            processed = process_document(document, processor)
            target.write(json.dumps(processed.to_dict(), ensure_ascii=False) + "\n")
            report.output_records += 1

    temporary_path.replace(output_path)
    return report
