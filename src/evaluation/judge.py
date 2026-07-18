"""Interactive pooled relevance judging for the evaluation query set."""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

from src.evaluation import (
    EvaluationQuery,
    RelevanceJudgment,
    load_judgments,
    load_queries,
    save_judgments,
)
from src.indexing import PositionalInvertedIndex
from src.retrieval import BM25FRetriever, TfidfRetriever

# These terms are used only to build a human-judging pool when the systems under
# evaluation return nothing. The actual experiment still runs the original
# query, so a failed lexical match remains visible in the reported metrics.
JUDGING_POOL_EXPANSIONS = {
    "hải sản": "cá tôm mực nghêu ốc",
}


def pooled_document_ids(
    query: EvaluationQuery,
    tfidf: TfidfRetriever,
    bm25f: BM25FRetriever,
    *,
    pool_depth: int,
) -> list[str]:
    """Fuse both rankings into an unbiased deterministic judging pool."""

    if pool_depth <= 0:
        raise ValueError("pool_depth must be positive")
    def collect(query_text: str) -> tuple[dict[str, float], dict[str, int]]:
        fusion_scores: dict[str, float] = defaultdict(float)
        best_rank: dict[str, int] = {}
        for retriever in (tfidf, bm25f):
            results = retriever.search(
                query_text,
                top_k=pool_depth,
                filters=query.filters,
            )
            for rank, result in enumerate(results, start=1):
                fusion_scores[result.doc_id] += 1.0 / (60 + rank)
                best_rank[result.doc_id] = min(rank, best_rank.get(result.doc_id, rank))
        return fusion_scores, best_rank

    fusion_scores, best_rank = collect(query.text)
    if not fusion_scores:
        expanded_text = JUDGING_POOL_EXPANSIONS.get(query.text.casefold().strip())
        if expanded_text:
            fusion_scores, best_rank = collect(expanded_text)
    return sorted(
        fusion_scores,
        key=lambda doc_id: (-fusion_scores[doc_id], best_rank[doc_id], doc_id),
    )


def _print_candidate(
    query: EvaluationQuery,
    document: dict[str, object],
    position: int,
    total: int,
) -> None:
    print("\n" + "=" * 72)
    print(f"{query.query_id}: {query.text}")
    print(f"Ý định: {query.intent}")
    if query.filters.active:
        print(f"Bộ lọc: {query.filters.to_dict()}")
    print(f"Ứng viên {position}/{total}: {document.get('title', '')}")
    print(f"Thời gian: {document.get('total_time_minutes')} | Độ khó: {document.get('difficulty')}")
    print(f"Danh mục: {', '.join(str(value) for value in document.get('categories', []))}")
    ingredients = [str(value) for value in document.get("ingredients", [])]
    print(f"Nguyên liệu: {', '.join(ingredients[:8])}")
    description = " ".join(str(document.get("description", "")).split())
    if description:
        print(f"Mô tả: {description[:240]}")
    print(f"URL: {document.get('url', '')}")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Create human qrels from a pooled ranking.")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--queries", default="data/ground_truth/queries.jsonl")
    parser.add_argument("--qrels", default="data/ground_truth/qrels.jsonl")
    parser.add_argument("--pool-depth", type=int, default=5)
    parser.add_argument("--query-id", help="Judge only one query ID.")
    parser.add_argument("--rejudge", action="store_true", help="Ask again for existing labels.")
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if args.pool_depth <= 0:
        raise SystemExit("--pool-depth must be positive")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    index_path = Path(args.index)
    if not index_path.exists():
        raise SystemExit("Index not found. Run `python -m src.indexing.build` first.")
    queries = load_queries(args.queries)
    if args.query_id:
        queries = [query for query in queries if query.query_id == args.query_id]
        if not queries:
            raise SystemExit(f"Unknown query ID: {args.query_id}")

    index = PositionalInvertedIndex.load(index_path)
    tfidf = TfidfRetriever(index)
    bm25f = BM25FRetriever(index)
    qrels_path = Path(args.qrels)
    judgments = {
        (item.query_id, item.doc_id): item for item in load_judgments(qrels_path)
    }

    print("Nhãn: 0=không liên quan, 1=liên quan, 2=rất liên quan, s=bỏ qua, q=thoát")
    for query in queries:
        candidate_ids = pooled_document_ids(
            query,
            tfidf,
            bm25f,
            pool_depth=args.pool_depth,
        )
        if not candidate_ids:
            print(f"\n{query.query_id}: không có ứng viên; hãy kiểm tra query/filter.")
            continue
        if query.text.casefold().strip() in JUDGING_POOL_EXPANSIONS:
            print(
                f"\n{query.query_id}: pool dự phòng có thể dùng từ mở rộng; "
                "evaluation vẫn chạy nguyên truy vấn."
            )
        for position, doc_id in enumerate(candidate_ids, start=1):
            key = (query.query_id, doc_id)
            if key in judgments and not args.rejudge:
                continue
            _print_candidate(query, index.documents[doc_id], position, len(candidate_ids))
            while True:
                try:
                    label = input("Mức liên quan [0/1/2/s/q]: ").strip().lower()
                except (EOFError, KeyboardInterrupt):
                    label = "q"
                if label in {"0", "1", "2"}:
                    judgments[key] = RelevanceJudgment(query.query_id, doc_id, int(label))
                    save_judgments(qrels_path, judgments.values())
                    break
                if label == "s":
                    break
                if label == "q":
                    save_judgments(qrels_path, judgments.values())
                    print(f"Đã lưu {len(judgments)} judgments vào {qrels_path}.")
                    return
                print("Chỉ nhập 0, 1, 2, s hoặc q.")

    save_judgments(qrels_path, judgments.values())
    positive_queries = {
        item.query_id for item in judgments.values() if item.relevance > 0
    }
    print(f"\nHoàn tất: {len(judgments)} judgments, {len(positive_queries)} query có relevant.")
    print(f"Đã lưu tại {qrels_path}.")


if __name__ == "__main__":
    main()
