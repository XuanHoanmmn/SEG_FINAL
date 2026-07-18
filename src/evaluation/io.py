"""Deterministic JSONL persistence for evaluation queries and qrels."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path
from typing import Any, TypeVar

from src.evaluation.models import EvaluationQuery, RelevanceJudgment

T = TypeVar("T")


def load_queries(path: str | Path) -> list[EvaluationQuery]:
    queries = _load_jsonl(path, EvaluationQuery.from_dict)
    _require_unique((query.query_id for query in queries), "query_id")
    return queries


def load_judgments(path: str | Path) -> list[RelevanceJudgment]:
    path = Path(path)
    if not path.exists():
        return []
    judgments = _load_jsonl(path, RelevanceJudgment.from_dict)
    keys = (f"{item.query_id}\0{item.doc_id}" for item in judgments)
    _require_unique(keys, "query-document judgment")
    return judgments


def save_judgments(path: str | Path, judgments: Iterable[RelevanceJudgment]) -> None:
    ordered = sorted(judgments, key=lambda item: (item.query_id, item.doc_id))
    _write_jsonl_atomic(path, (judgment.to_dict() for judgment in ordered))


def _load_jsonl(path: str | Path, factory: Any) -> list[T]:
    result: list[T] = []
    with Path(path).open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            try:
                result.append(factory(json.loads(line)))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
    return result


def _write_jsonl_atomic(path: str | Path, values: Iterable[dict[str, Any]]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
        for value in values:
            handle.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
    temporary_path.replace(path)


def _require_unique(values: Iterable[str], label: str) -> None:
    seen: set[str] = set()
    for value in values:
        if value in seen:
            raise ValueError(f"Duplicate {label}: {value.replace(chr(0), '/')}")
        seen.add(value)
