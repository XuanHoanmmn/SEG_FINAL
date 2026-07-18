import unittest

from src.evaluation import (
    QueryMetrics,
    average_precision,
    evaluate_ranking,
    mean_metrics,
    ndcg_at_k,
    percentile,
    precision_at_k,
    recall_at_k,
    reciprocal_rank_at_k,
)


class EvaluationMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.ranked = ["d2", "d1", "d3"]
        self.relevance = {"d1": 2, "d3": 1, "d4": 1}

    def test_binary_metrics_use_positive_graded_labels_as_relevant(self) -> None:
        self.assertEqual(precision_at_k(self.ranked, self.relevance, 2), 0.5)
        self.assertAlmostEqual(recall_at_k(self.ranked, self.relevance, 2), 1 / 3)
        self.assertEqual(reciprocal_rank_at_k(self.ranked, self.relevance, 10), 0.5)
        self.assertAlmostEqual(average_precision(self.ranked, self.relevance), 7 / 18)

    def test_ndcg_is_one_for_ideal_graded_order(self) -> None:
        ranked = ["high", "relevant", "irrelevant"]
        relevance = {"high": 2, "relevant": 1, "irrelevant": 0}

        self.assertEqual(ndcg_at_k(ranked, relevance, 10), 1.0)
        self.assertLess(ndcg_at_k(list(reversed(ranked)), relevance, 10), 1.0)

    def test_evaluate_and_average_metrics(self) -> None:
        first = evaluate_ranking(self.ranked, self.relevance)
        second = QueryMetrics(0.0, 0.0, 0.0, 0.0, 0.0)
        averaged = mean_metrics([first, second])

        self.assertEqual(averaged.precision_at_10, first.precision_at_10 / 2)
        self.assertEqual(mean_metrics([]), second)

    def test_percentile_interpolates_and_validates_range(self) -> None:
        self.assertEqual(percentile([10.0, 20.0, 30.0], 50), 20.0)
        self.assertEqual(percentile([10.0, 20.0], 95), 19.5)
        self.assertEqual(percentile([], 50), 0.0)
        with self.assertRaisesRegex(ValueError, "between"):
            percentile([1.0], 101)

    def test_metrics_reject_non_positive_cutoff(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            precision_at_k(self.ranked, self.relevance, 0)


if __name__ == "__main__":
    unittest.main()
