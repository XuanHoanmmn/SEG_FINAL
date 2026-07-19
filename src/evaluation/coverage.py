"""Audit corpus scope and probe representative recipe queries."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from src.indexing import PositionalInvertedIndex, build_corpus_profile
from src.preprocessing import normalize_text
from src.retrieval import BM25FRetriever

DEFAULT_PROBE_QUERIES = (
    "gà nướng",
    "canh chua",
    "món chay",
    "hải sản",
    "phở",
    "pizza",
)


def probe_queries(
    index: PositionalInvertedIndex,
    queries: Iterable[str],
    *,
    top_k: int = 3,
) -> list[dict[str, Any]]:
    """Run deterministic BM25F probes and expose real indexed coverage."""

    if top_k <= 0:
        raise ValueError("top_k must be positive")
    retriever = BM25FRetriever(index)
    probes: list[dict[str, Any]] = []
    seen: set[str] = set()
    for query in queries:
        display_query = " ".join(str(query).split())
        normalized = normalize_text(display_query)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        results = retriever.search(display_query, top_k=max(top_k, len(index)))
        probes.append(
            {
                "query": display_query,
                "normalized": normalized,
                "covered": bool(results),
                "result_count": len(results),
                "top_results": [
                    {
                        "doc_id": result.doc_id,
                        "title": result.title,
                        "score": round(result.score, 6),
                        "matched_terms": list(result.matched_terms),
                        "matched_fields": list(result.matched_fields),
                    }
                    for result in results[:top_k]
                ],
            }
        )
    return probes


def build_coverage_audit(
    index: PositionalInvertedIndex,
    queries: Iterable[str] = DEFAULT_PROBE_QUERIES,
    *,
    top_k: int = 3,
) -> dict[str, Any]:
    """Build one reproducible report for corpus scope and query coverage."""

    return {
        "index": index.statistics().to_dict(),
        "corpus": build_corpus_profile(index),
        "query_probes": probe_queries(index, queries, top_k=top_k),
    }


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
        description="Report indexed recipe scope and test representative queries."
    )
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--output", default="artifacts/corpus_coverage.json")
    parser.add_argument(
        "--query",
        action="append",
        dest="queries",
        help="Probe one query; repeat the option for more queries.",
    )
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.top_k <= 0:
        raise SystemExit("--top-k must be positive")
    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit("Index not found. Run `python -m src.indexing.build` first.")
    queries = args.queries or DEFAULT_PROBE_QUERIES
    report = build_coverage_audit(
        PositionalInvertedIndex.load(index_path),
        queries,
        top_k=args.top_k,
    )
    _write_json_atomic(args.output, report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"Đã lưu báo cáo: {args.output}")


if __name__ == "__main__":
    main()
