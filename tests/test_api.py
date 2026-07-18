import unittest

from src.api import create_app
from src.indexing import build_inverted_index
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document


def build_api_index():
    documents = [
        RecipeDocument(
            doc_id="chicken-grill",
            title="Gà nướng mật ong",
            url="https://example.com/chicken-grill",
            source="example.com",
            description="Thịt gà nướng thơm và mềm.",
            ingredients=["thịt gà", "mật ong"],
            instructions=["Ướp gà", "Nướng chín"],
            categories=["Món mặn", "Bữa tối"],
            cooking_method="nướng",
            cook_time_minutes=30,
            difficulty="Dễ",
        ),
        RecipeDocument(
            doc_id="chicken-soup",
            title="Súp gà nấm",
            url="https://example.com/chicken-soup",
            source="example.com",
            description="Món súp nóng cho bữa sáng.",
            ingredients=["thịt gà", "nấm"],
            instructions=["Nấu súp"],
            categories=["Món mặn", "Bữa sáng"],
            cooking_method="súp",
            cook_time_minutes=15,
            difficulty="Dễ",
        ),
        RecipeDocument(
            doc_id="seafood",
            title="Mực chiên giòn",
            url="https://example.com/seafood",
            source="example.com",
            description="Mực giòn dùng nóng.",
            ingredients=["mực ống"],
            instructions=["Chiên mực"],
            categories=["Món mặn"],
            cooking_method="chiên",
            cook_time_minutes=20,
            difficulty="Trung bình",
        ),
    ]
    processor = VietnameseTextProcessor(use_word_segmentation=False)
    return build_inverted_index([process_document(document, processor) for document in documents])


class SearchAPITests(unittest.TestCase):
    def setUp(self) -> None:
        app = create_app(index=build_api_index())
        app.config.update(TESTING=True)
        self.client = app.test_client()

    def test_health_reports_loaded_index_and_rankers(self) -> None:
        response = self.client.get("/api/v1/health")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["status"], "ok")
        self.assertEqual(payload["index"]["document_count"], 3)
        self.assertEqual(payload["rankers"], ["bm25f", "tfidf"])
        self.assertEqual(response.headers["X-API-Version"], "1.0")

    def test_search_paginates_and_returns_facets_and_explanation(self) -> None:
        response = self.client.get(
            "/api/v1/search",
            query_string={"q": "gà", "page": 1, "page_size": 1},
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["pagination"]["total_results"], 2)
        self.assertEqual(payload["pagination"]["total_pages"], 2)
        self.assertTrue(payload["pagination"]["has_next"])
        self.assertEqual(len(payload["results"]), 1)
        self.assertIn("title", payload["results"][0]["explanation"]["matched_fields"])
        category_facets = {item["value"]: item["count"] for item in payload["facets"]["categories"]}
        self.assertEqual(category_facets["Món mặn"], 2)

    def test_accentless_query_returns_safe_highlight_offsets(self) -> None:
        response = self.client.get(
            "/api/v1/search",
            query_string={"q": "ga nuong", "page_size": 5},
        )
        result = response.get_json()["results"][0]
        snippet = result["snippet"]

        self.assertEqual(result["doc_id"], "chicken-grill")
        self.assertEqual(snippet["field"], "title")
        self.assertTrue(snippet["highlights"])
        for highlight in snippet["highlights"]:
            self.assertGreater(highlight["end"], highlight["start"])
            self.assertLessEqual(highlight["end"], len(snippet["text"]))

    def test_bm25f_expands_seafood_but_tfidf_remains_literal(self) -> None:
        bm25f_response = self.client.get("/api/v1/search", query_string={"q": "hải sản"})
        tfidf_response = self.client.get(
            "/api/v1/search",
            query_string={"q": "hải sản", "ranker": "tfidf"},
        )

        bm25f = bm25f_response.get_json()
        tfidf = tfidf_response.get_json()
        self.assertEqual(bm25f["results"][0]["doc_id"], "seafood")
        self.assertIn("mực", bm25f["query"]["expanded_terms"])
        self.assertEqual(tfidf["pagination"]["total_results"], 0)
        self.assertEqual(tfidf["query"]["expanded_terms"], [])

    def test_structured_filters_are_applied_before_pagination(self) -> None:
        response = self.client.get(
            "/api/v1/search",
            query_string={
                "q": "gà",
                "category": "Bữa sáng",
                "max_time": 15,
            },
        )
        payload = response.get_json()

        self.assertEqual(payload["pagination"]["total_results"], 1)
        self.assertEqual(payload["results"][0]["doc_id"], "chicken-soup")

    def test_validation_errors_use_stable_json_shape(self) -> None:
        cases = (
            ("/api/v1/search", "missing_query"),
            ("/api/v1/search?q=gà&page=zero", "invalid_parameter"),
            ("/api/v1/search?q=gà&page_size=51", "invalid_parameter"),
            ("/api/v1/search?q=gà&ranker=unknown", "invalid_ranker"),
        )
        for url, expected_code in cases:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["error"]["code"], expected_code)

    def test_unknown_endpoint_is_json(self) -> None:
        response = self.client.get("/api/v1/unknown")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json()["error"]["code"], "not_found")


if __name__ == "__main__":
    unittest.main()
