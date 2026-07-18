import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation import (
    RelevanceJudgment,
    load_judgments,
    load_queries,
    save_judgments,
)


class EvaluationIOTests(unittest.TestCase):
    def test_loads_query_filters_and_round_trips_sorted_qrels(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queries_path = root / "queries.jsonl"
            qrels_path = root / "qrels.jsonl"
            queries_path.write_text(
                json.dumps(
                    {
                        "query_id": "q1",
                        "text": "ga nuong",
                        "intent": "accentless",
                        "filters": {"max_time_minutes": 15, "categories": ["Món mặn"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            queries = load_queries(queries_path)
            judgments = [
                RelevanceJudgment("q1", "d2", 1),
                RelevanceJudgment("q1", "d1", 2),
            ]
            save_judgments(qrels_path, judgments)
            loaded_judgments = load_judgments(qrels_path)

        self.assertEqual(queries[0].filters.max_time_minutes, 15)
        self.assertEqual(queries[0].filters.categories, ("Món mặn",))
        self.assertEqual([item.doc_id for item in loaded_judgments], ["d1", "d2"])

    def test_missing_qrels_is_an_empty_resumable_set(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            self.assertEqual(load_judgments(Path(directory) / "missing.jsonl"), [])

    def test_rejects_duplicate_query_ids_and_invalid_relevance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "queries.jsonl"
            record = json.dumps({"query_id": "q1", "text": "gà"})
            path.write_text(f"{record}\n{record}\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "Duplicate"):
                load_queries(path)
        with self.assertRaisesRegex(ValueError, "0, 1 or 2"):
            RelevanceJudgment("q1", "d1", 3)


if __name__ == "__main__":
    unittest.main()
