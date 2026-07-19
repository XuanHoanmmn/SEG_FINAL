import unittest

from src.evaluation.coverage import build_coverage_audit, probe_queries
from src.indexing import build_corpus_profile, build_inverted_index
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document


def build_coverage_index():
    documents = [
        RecipeDocument(
            doc_id="pho-bo",
            title="Phở bò",
            url="https://example.com/pho-bo",
            source="example.com",
            description="Món phở truyền thống.",
            ingredients=["bánh phở", "thịt bò"],
            instructions=["Nấu nước dùng"],
            categories=["Món Việt", "Món nước"],
            cooking_method="nấu",
            cook_time_minutes=60,
            difficulty="Trung bình",
        ),
        RecipeDocument(
            doc_id="pizza",
            title="Pizza thịt nguội",
            url="https://example.com/pizza",
            source="example.com",
            ingredients=["bột mì", "thịt nguội"],
            instructions=["Nướng bánh"],
            categories=["Món Âu"],
            cooking_method="nướng",
            cook_time_minutes=25,
            difficulty="Dễ",
        ),
    ]
    processor = VietnameseTextProcessor(use_word_segmentation=False)
    return build_inverted_index(
        process_document(document, processor) for document in documents
    )


class CorpusCoverageTests(unittest.TestCase):
    def setUp(self) -> None:
        self.index = build_coverage_index()

    def test_profile_counts_distributions_and_missing_fields(self) -> None:
        profile = build_corpus_profile(self.index)

        self.assertEqual(profile["document_count"], 2)
        self.assertEqual(profile["sources"], [{"value": "example.com", "count": 2}])
        self.assertEqual(profile["categories"][0], {"value": "Món nước", "count": 1})
        self.assertEqual(profile["field_completeness"]["description"]["present"], 1)
        self.assertEqual(profile["field_completeness"]["description"]["ratio"], 0.5)
        self.assertEqual(profile["field_completeness"]["image_url"]["missing"], 2)

    def test_query_probes_distinguish_covered_and_missing_dishes(self) -> None:
        probes = probe_queries(
            self.index,
            ["phở", "pho", "pizza", "sushi", "phở"],
            top_k=1,
        )

        by_query = {probe["query"]: probe for probe in probes}
        self.assertEqual(len(probes), 4)
        self.assertTrue(by_query["phở"]["covered"])
        self.assertEqual(by_query["phở"]["top_results"][0]["doc_id"], "pho-bo")
        self.assertTrue(by_query["pho"]["covered"])
        self.assertTrue(by_query["pizza"]["covered"])
        self.assertFalse(by_query["sushi"]["covered"])
        self.assertEqual(by_query["sushi"]["result_count"], 0)

    def test_complete_audit_contains_index_profile_and_probes(self) -> None:
        report = build_coverage_audit(self.index, ["phở", "pizza"], top_k=2)

        self.assertEqual(report["index"]["document_count"], 2)
        self.assertEqual(report["corpus"]["document_count"], 2)
        self.assertEqual([item["query"] for item in report["query_probes"]], ["phở", "pizza"])

    def test_probe_rejects_invalid_depth(self) -> None:
        with self.assertRaisesRegex(ValueError, "positive"):
            probe_queries(self.index, ["phở"], top_k=0)


if __name__ == "__main__":
    unittest.main()
