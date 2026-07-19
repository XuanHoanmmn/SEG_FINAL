"""Command-line pipeline for processed data and the custom inverted index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from src.indexing import build_corpus_profile, build_inverted_index
from src.preprocessing import (
    VietnameseTextProcessor,
    iter_processed_jsonl,
    process_jsonl,
)


def build_pipeline(
    raw_path: str | Path,
    processed_path: str | Path,
    index_path: str | Path,
    report_path: str | Path,
    *,
    use_word_segmentation: bool = True,
) -> dict[str, Any]:
    """Build reproducible processed JSONL, index artifact and quality report."""

    processor = VietnameseTextProcessor(use_word_segmentation=use_word_segmentation)
    processing_report = process_jsonl(raw_path, processed_path, processor)
    index = build_inverted_index(iter_processed_jsonl(processed_path))
    index.save(index_path)

    report = {
        "processing": processing_report.to_dict(),
        "index": index.statistics().to_dict(),
        "coverage": build_corpus_profile(index),
        "paths": {
            "raw": str(raw_path),
            "processed": str(processed_path),
            "index": str(index_path),
        },
        "word_segmentation": processor.segmenter is not None,
    }
    _write_json_atomic(report_path, report)
    return report


def _write_json_atomic(path: str | Path, value: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary_path.replace(path)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Preprocess crawled recipes and build the positional inverted index."
    )
    parser.add_argument("--input", default="data/raw/mnmn_recipes.jsonl")
    parser.add_argument("--processed", default="data/processed/recipes.jsonl")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--report", default="artifacts/index_report.json")
    parser.add_argument(
        "--no-word-segmentation",
        action="store_true",
        help="Use the deterministic basic tokenizer instead of underthesea.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    report = build_pipeline(
        args.input,
        args.processed,
        args.index,
        args.report,
        use_word_segmentation=not args.no_word_segmentation,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
