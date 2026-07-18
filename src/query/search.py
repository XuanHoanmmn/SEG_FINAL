"""Command-line interface for the TF-IDF recipe search baseline."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from time import perf_counter
from typing import Protocol

from src.indexing import PositionalInvertedIndex
from src.query import SearchFilters
from src.retrieval import BM25FRetriever, SearchResult, TfidfRetriever


class SearchBackend(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]: ...


def search_once(
    retriever: SearchBackend,
    query: str,
    *,
    top_k: int,
    filters: SearchFilters | None = None,
) -> tuple[list[SearchResult], float]:
    started_at = perf_counter()
    results = retriever.search(query, top_k=top_k, filters=filters)
    elapsed_ms = (perf_counter() - started_at) * 1000
    return results, elapsed_ms


def _print_results(
    query: str,
    results: list[SearchResult],
    elapsed_ms: float,
    ranking_model: str,
) -> None:
    print(
        f'\nTruy vấn: "{query}" — {len(results)} kết quả '
        f"({elapsed_ms:.2f} ms, {ranking_model.upper()})"
    )
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


def _print_json(
    query: str,
    results: list[SearchResult],
    elapsed_ms: float,
    ranking_model: str,
    filters: SearchFilters,
) -> None:
    payload = {
        "query": query,
        "ranking_model": ranking_model,
        "filters": filters.to_dict(),
        "elapsed_ms": round(elapsed_ms, 3),
        "total": len(results),
        "results": [result.to_dict() for result in results],
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def _interactive(
    retriever: SearchBackend,
    top_k: int,
    ranking_model: str,
    filters: SearchFilters,
) -> None:
    print(f"Vietnamese Recipe Search — {ranking_model.upper()}")
    print("Nhập truy vấn; nhập 'quit' hoặc để trống để thoát.")
    if filters.active:
        print(f"Bộ lọc: {json.dumps(filters.to_dict(), ensure_ascii=False)}")
    while True:
        try:
            query = input("\nTìm món> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if not query or query.lower() in {"exit", "q", "quit"}:
            return
        results, elapsed_ms = search_once(
            retriever,
            query,
            top_k=top_k,
            filters=filters,
        )
        _print_results(query, results, elapsed_ms, ranking_model)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Search recipes with the TF-IDF baseline.")
    parser.add_argument("query", nargs="*", help="Query text; omit it for interactive mode.")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--ranker", choices=("bm25f", "tfidf"), default="bm25f")
    parser.add_argument("--max-time", type=int, help="Maximum total/cooking time in minutes.")
    parser.add_argument("--difficulty", help="Difficulty such as Dễ, Vừa or Khó.")
    parser.add_argument("--category", action="append", default=[])
    parser.add_argument("--ingredient", action="append", default=[])
    parser.add_argument("--method", action="append", default=[])
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    return parser.parse_args()


def _build_filters(args: argparse.Namespace) -> SearchFilters:
    return SearchFilters(
        max_time_minutes=args.max_time,
        difficulty=args.difficulty,
        categories=tuple(args.category),
        ingredients=tuple(args.ingredient),
        cooking_methods=tuple(args.method),
    )


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

    index = PositionalInvertedIndex.load(index_path)
    retriever: SearchBackend
    if args.ranker == "tfidf":
        retriever = TfidfRetriever(index)
    else:
        retriever = BM25FRetriever(index)
    filters = _build_filters(args)
    query = " ".join(args.query).strip()
    if not query:
        if args.json:
            raise SystemExit("A query is required with --json")
        _interactive(retriever, args.top_k, args.ranker, filters)
        return

    results, elapsed_ms = search_once(
        retriever,
        query,
        top_k=args.top_k,
        filters=filters,
    )
    if args.json:
        _print_json(query, results, elapsed_ms, args.ranker, filters)
    else:
        _print_results(query, results, elapsed_ms, args.ranker)


if __name__ == "__main__":
    main()
