import csv
import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation import EvaluationQuery
from src.evaluation.judge import pooled_document_ids
from src.evaluation.run import run_evaluation, save_evaluation_report
from src.indexing import build_inverted_index
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document
from src.query import QueryProcessor
from src.retrieval import BM25FRetriever, TfidfRetriever


def build_test_index():
    documents = [
        RecipeDocument(
            doc_id="chicken",
            title="Gà nướng mật ong",
            url="https://example.com/chicken",
            source="example.com",
            ingredients=["gà", "mật ong"],
            instructions=["nướng gà"],
            content_hash="hash-chicken",
        ),
        RecipeDocument(
            doc_id="soup",
            title="Súp gà",
            url="https://example.com/soup",
            source="example.com",
            ingredients=["gà", "nấm"],
            instructions=["nấu súp"],
            content_hash="hash-soup",
        ),
        RecipeDocument(
            doc_id="salad",
            title="Salad rau củ",
            url="https://example.com/salad",
            source="example.com",
            ingredients=["rau", "cà chua"],
            instructions=["trộn salad"],
            content_hash="hash-salad",
        ),
        RecipeDocument(
            doc_id="seafood",
            title="Mực chiên giòn",
            url="https://example.com/seafood",
            source="example.com",
            ingredients=["mực", "bột chiên"],
            instructions=["chiên mực"],
            content_hash="hash-seafood",
        ),
    ]
    processor = VietnameseTextProcessor(use_word_segmentation=False)
    return (
        build_inverted_index([process_document(document, processor) for document in documents]),
        processor,
    )


class EvaluationRunnerTests(unittest.TestCase):
    def test_pooled_ids_include_candidates_from_both_rankers(self) -> None:
        index, processor = build_test_index()
        query_processor = QueryProcessor(processor)
        query = EvaluationQuery("q1", "gà nướng")

        pooled = pooled_document_ids(
            query,
            TfidfRetriever(index, query_processor=query_processor),
            BM25FRetriever(index, query_processor=query_processor),
            pool_depth=2,
        )

        self.assertEqual(pooled[0], "chicken")
        self.assertIn("soup", pooled)

    def test_pooled_ids_expand_only_when_original_query_has_no_results(self) -> None:
        index, processor = build_test_index()
        query_processor = QueryProcessor(processor)

        pooled = pooled_document_ids(
            EvaluationQuery("q19", "hải sản"),
            TfidfRetriever(index, query_processor=query_processor),
            BM25FRetriever(index, query_processor=query_processor),
            pool_depth=5,
        )

        self.assertIn("seafood", pooled)

    def test_run_evaluation_compares_both_models(self) -> None:
        index, _ = build_test_index()
        queries = [EvaluationQuery("q1", "gà nướng"), EvaluationQuery("q2", "salad")]
        relevance = {
            "q1": {"chicken": 2, "soup": 1},
            "q2": {"salad": 2},
        }

        report = run_evaluation(index, queries, relevance, latency_runs=1)

        self.assertEqual([model["model"] for model in report["models"]], ["tfidf", "bm25f"])
        self.assertEqual(report["query_count"], 2)
        self.assertIn("ndcg_at_10", report["models"][0]["summary"])
        self.assertIn("map", report["bm25f_minus_tfidf"])

    def test_rejects_queries_without_positive_qrels(self) -> None:
        index, _ = build_test_index()

        with self.assertRaisesRegex(ValueError, "q1"):
            run_evaluation(
                index,
                [EvaluationQuery("q1", "gà")],
                {"q1": {"chicken": 0}},
                latency_runs=1,
            )

    def test_report_writes_json_and_excel_friendly_csv(self) -> None:
        index, _ = build_test_index()
        report = run_evaluation(
            index,
            [EvaluationQuery("q1", "gà")],
            {"q1": {"chicken": 2, "soup": 1}},
            latency_runs=1,
        )
        with tempfile.TemporaryDirectory() as directory:
            json_path = Path(directory) / "report.json"
            csv_path = Path(directory) / "results.csv"
            save_evaluation_report(report, json_path, csv_path)
            loaded_report = json.loads(json_path.read_text(encoding="utf-8"))
            with csv_path.open(encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))

        self.assertEqual(loaded_report["query_count"], 1)
        self.assertEqual(len(rows), 2)
        self.assertEqual({row["model"] for row in rows}, {"tfidf", "bm25f"})


if __name__ == "__main__":
    unittest.main()
