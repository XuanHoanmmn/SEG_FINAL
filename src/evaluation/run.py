"""Compare TF-IDF and BM25F on the same human-judged query set."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from pathlib import Path
from time import perf_counter
from typing import Any, Protocol

from src.evaluation import (
    EvaluationQuery,
    QueryMetrics,
    evaluate_ranking,
    load_judgments,
    load_queries,
    mean_metrics,
    percentile,
)
from src.indexing import PositionalInvertedIndex
from src.query import SearchFilters
from src.retrieval import BM25FRetriever, SearchResult, TfidfRetriever


class EvaluationRanker(Protocol):
    def search(
        self,
        query: str,
        *,
        top_k: int = 10,
        filters: SearchFilters | None = None,
    ) -> list[SearchResult]: ...


def evaluate_model(
    model_name: str,
    ranker: EvaluationRanker,
    queries: list[EvaluationQuery],
    relevance_by_query: dict[str, dict[str, int]],
    *,
    result_depth: int,
    latency_runs: int,
) -> dict[str, Any]:
    if result_depth <= 0 or latency_runs <= 0:
        raise ValueError("result_depth and latency_runs must be positive")

    per_query: list[dict[str, Any]] = []
    all_metrics: list[QueryMetrics] = []
    latency_values: list[float] = []
    for query in queries:
        run_latencies: list[float] = []
        results: list[SearchResult] = []
        for _ in range(latency_runs):
            started_at = perf_counter()
            results = ranker.search(
                query.text,
                top_k=result_depth,
                filters=query.filters,
            )
            run_latencies.append((perf_counter() - started_at) * 1000)
        latency_ms = percentile(run_latencies, 50)
        latency_values.append(latency_ms)
        relevance = relevance_by_query[query.query_id]
        metrics = evaluate_ranking([result.doc_id for result in results], relevance)
        all_metrics.append(metrics)
        per_query.append(
            {
                "model": model_name,
                "query_id": query.query_id,
                "query": query.text,
                "metrics": metrics.to_dict(),
                "latency_ms": latency_ms,
                "result_count": len(results),
                "relevant_count": sum(value > 0 for value in relevance.values()),
                "top_10_doc_ids": [result.doc_id for result in results[:10]],
            }
        )

    summary_metrics = mean_metrics(all_metrics).to_dict()
    return {
        "model": model_name,
        "query_count": len(queries),
        "summary": {
            **summary_metrics,
            "map": summary_metrics["average_precision"],
            "mrr_at_10": summary_metrics["reciprocal_rank_at_10"],
            "latency_p50_ms": percentile(latency_values, 50),
            "latency_p95_ms": percentile(latency_values, 95),
        },
        "per_query": per_query,
    }


def run_evaluation(
    index: PositionalInvertedIndex,
    queries: list[EvaluationQuery],
    relevance_by_query: dict[str, dict[str, int]],
    *,
    latency_runs: int = 3,
) -> dict[str, Any]:
    _validate_ground_truth(queries, relevance_by_query)
    depth = max(20, len(index))
    models = [
        evaluate_model(
            "tfidf",
            TfidfRetriever(index),
            queries,
            relevance_by_query,
            result_depth=depth,
            latency_runs=latency_runs,
        ),
        evaluate_model(
            "bm25f",
            BM25FRetriever(index),
            queries,
            relevance_by_query,
            result_depth=depth,
            latency_runs=latency_runs,
        ),
    ]
    summaries = {model["model"]: model["summary"] for model in models}
    comparison_keys = (
        "precision_at_10",
        "map",
        "recall_at_20",
        "mrr_at_10",
        "ndcg_at_10",
    )
    return {
        "query_count": len(queries),
        "judgment_count": sum(len(values) for values in relevance_by_query.values()),
        "models": models,
        "bm25f_minus_tfidf": {
            key: summaries["bm25f"][key] - summaries["tfidf"][key]
            for key in comparison_keys
        },
    }


def _validate_ground_truth(
    queries: list[EvaluationQuery],
    relevance_by_query: dict[str, dict[str, int]],
) -> None:
    missing = [
        query.query_id
        for query in queries
        if not any(value > 0 for value in relevance_by_query.get(query.query_id, {}).values())
    ]
    if missing:
        raise ValueError(
            "Every query needs at least one relevant judgment. Missing: " + ", ".join(missing)
        )


def _write_json_atomic(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    with temporary_path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)
        handle.write("\n")
    temporary_path.replace(path)


def _write_csv_atomic(path: str | Path, report: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(f"{path.suffix}.tmp")
    columns = [
        "model",
        "query_id",
        "query",
        "precision_at_10",
        "average_precision",
        "recall_at_20",
        "reciprocal_rank_at_10",
        "ndcg_at_10",
        "latency_ms",
        "result_count",
        "relevant_count",
    ]
    with temporary_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for model in report["models"]:
            for row in model["per_query"]:
                writer.writerow(
                    {
                        **{key: row[key] for key in columns if key in row},
                        **row["metrics"],
                    }
                )
    temporary_path.replace(path)


def save_evaluation_report(
    report: dict[str, Any],
    json_path: str | Path,
    csv_path: str | Path,
) -> None:
    """Persist the complete report and its Excel-friendly per-query table."""

    _write_json_atomic(json_path, report)
    _write_csv_atomic(csv_path, report)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate TF-IDF and BM25F.")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--queries", default="data/ground_truth/queries.jsonl")
    parser.add_argument("--qrels", default="data/ground_truth/qrels.jsonl")
    parser.add_argument("--json", default="artifacts/evaluation_report.json")
    parser.add_argument("--csv", default="artifacts/evaluation_results.csv")
    parser.add_argument("--latency-runs", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.latency_runs <= 0:
        raise SystemExit("--latency-runs must be positive")

    queries = load_queries(args.queries)
    judgments = load_judgments(args.qrels)
    relevance_by_query: dict[str, dict[str, int]] = defaultdict(dict)
    for item in judgments:
        relevance_by_query[item.query_id][item.doc_id] = item.relevance
    try:
        report = run_evaluation(
            PositionalInvertedIndex.load(args.index),
            queries,
            relevance_by_query,
            latency_runs=args.latency_runs,
        )
    except (FileNotFoundError, ValueError) as exc:
        raise SystemExit(
            f"Evaluation cannot run: {exc}\n"
            "Create/complete qrels with `python -m src.evaluation.judge` first."
        ) from exc

    save_evaluation_report(report, args.json, args.csv)
    for model in report["models"]:
        summary = model["summary"]
        print(
            f"{model['model'].upper()}: P@10={summary['precision_at_10']:.4f} "
            f"MAP={summary['map']:.4f} Recall@20={summary['recall_at_20']:.4f} "
            f"MRR@10={summary['mrr_at_10']:.4f} nDCG@10={summary['ndcg_at_10']:.4f} "
            f"p50={summary['latency_p50_ms']:.2f}ms p95={summary['latency_p95_ms']:.2f}ms"
        )
    print(f"Đã lưu JSON: {args.json}")
    print(f"Đã lưu CSV: {args.csv}")


if __name__ == "__main__":
    main()
