"""Command-line interface for the TF-IDF recipe search baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter

from src.indexing import PositionalInvertedIndex
from src.retrieval import SearchResult, TfidfRetriever


def search_once(
    retriever: TfidfRetriever,
    query: str,
    *,
    top_k: int,
) -> tuple[list[SearchResult], float]:
    started_at = perf_counter()
    results = retriever.search(query, top_k=top_k)
    elapsed_ms = (perf_counter() - started_at) * 1000
    return results, elapsed_ms


def _print_results(query: str, results: list[SearchResult], elapsed_ms: float) -> None:
    print(f'\nTruy vấn: "{query}" — {len(results)} kết quả ({elapsed_ms:.2f} ms)')
    if not results:
        print("Không tìm thấy công thức phù hợp.")
        return

    for rank, result in enumerate(results, start=1):
        fields = ", ".join(result.matched_fields)
        terms = ", ".join(result.matched_terms)
        details = []
        if result.cook_time_minutes is not None:
            details.append(f"{result.cook_time_minutes} phút")
        if result.difficulty:
            details.append(result.difficulty)
        print(f"\n{rank}. {result.title}  [score={result.score:.4f}]")
        if details:
            print(f"   {' | '.join(details)}")
        print(f"   Khớp từ: {terms}")
        print(f"   Trong trường: {fields}")
        print(f"   {result.url}")


def _print_json(query: str, results: list[SearchResult], elapsed_ms: float) -> None:
    payload = {
        "query": query,
        "elapsed_ms": round(elapsed_ms, 3),
        "total": len(results),
        "results": [result.to_dict() for result in results],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _interactive(retriever: TfidfRetriever, top_k: int) -> None:
    print("Vietnamese Recipe Search — TF-IDF baseline")
    print("Nhập truy vấn; nhập 'quit' hoặc để trống để thoát.")
    while True:
        try:
            query = input("\nTìm món> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query or query.lower() in {"exit", "q", "quit"}:
            return
        results, elapsed_ms = search_once(retriever, query, top_k=top_k)
        _print_results(query, results, elapsed_ms)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search recipes with the TF-IDF baseline.")
    parser.add_argument("query", nargs="*", help="Query text; omit it for interactive mode.")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.top_k <= 0:
        raise SystemExit("--top-k must be a positive integer")

    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit(
            f"Index not found: {index_path}. Run `python -m src.indexing.build` first."
        )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    retriever = TfidfRetriever(PositionalInvertedIndex.load(index_path))
    query = " ".join(args.query).strip()
    if not query:
        if args.json:
            raise SystemExit("A query is required with --json")
        _interactive(retriever, args.top_k)
        return

    results, elapsed_ms = search_once(retriever, query, top_k=args.top_k)
    if args.json:
        _print_json(query, results, elapsed_ms)
    else:
        _print_results(query, results, elapsed_ms)


if __name__ == "__main__":
    main()
