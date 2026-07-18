import unittest

from src.indexing import build_inverted_index
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document
from src.query import QueryProcessor, SearchFilters
from src.retrieval import BM25FRetriever


def make_document(
    doc_id: str,
    *,
    title: str,
    description: str = "",
    ingredients: list[str] | None = None,
    categories: list[str] | None = None,
    cook_time: int = 20,
    difficulty: str = "Dễ",
    method: str | None = None,
) -> RecipeDocument:
    return RecipeDocument(
        doc_id=doc_id,
        title=title,
        url=f"https://example.com/{doc_id}",
        source="example.com",
        description=description,
        ingredients=ingredients or ["nước"],
        instructions=["chuẩn bị món ăn"],
        categories=categories or [],
        cooking_method=method,
        cook_time_minutes=cook_time,
        difficulty=difficulty,
        content_hash=f"hash-{doc_id}",
    )


def make_retriever(documents: list[RecipeDocument], **kwargs) -> BM25FRetriever:
    text_processor = VietnameseTextProcessor(use_word_segmentation=False)
    recipes = [process_document(document, text_processor) for document in documents]
    return BM25FRetriever(
        build_inverted_index(recipes),
        query_processor=QueryProcessor(text_processor),
        **kwargs,
    )


class BM25FRetrieverTests(unittest.TestCase):
    def test_field_weighting_prefers_title_match(self) -> None:
        retriever = make_retriever(
            [
                make_document("title", title="Gà", description="món"),
                make_document("description", title="Món", description="gà"),
            ]
        )

        results = retriever.search("gà")

        self.assertEqual([result.doc_id for result in results], ["title", "description"])
        self.assertGreater(results[0].score, results[1].score)

    def test_exact_phrase_ranks_above_reversed_terms(self) -> None:
        retriever = make_retriever(
            [
                make_document("exact", title="Gà nướng"),
                make_document("reversed", title="Nướng gà"),
            ]
        )

        results = retriever.search("gà nướng")

        self.assertEqual(results[0].doc_id, "exact")
        self.assertGreater(results[0].score, results[1].score)

    def test_nearer_terms_receive_larger_proximity_boost(self) -> None:
        retriever = make_retriever(
            [
                make_document("near", title="Gà rất ngon"),
                make_document("far", title="Gà rất thơm hấp dẫn ngon"),
            ],
            phrase_boost=0.0,
            proximity_boost=3.0,
        )

        results = retriever.search("gà ngon")

        self.assertEqual(results[0].doc_id, "near")
        self.assertGreater(results[0].score, results[1].score)

    def test_filters_are_applied_before_ranking(self) -> None:
        retriever = make_retriever(
            [
                make_document(
                    "fast-vegan",
                    title="Đậu hũ nướng",
                    ingredients=["đậu hũ"],
                    categories=["Món chay"],
                    cook_time=10,
                    method="nướng",
                ),
                make_document(
                    "slow-meat",
                    title="Gà nướng",
                    ingredients=["thịt gà"],
                    categories=["Món mặn"],
                    cook_time=60,
                    method="nướng",
                ),
            ]
        )
        filters = SearchFilters(
            max_time_minutes=15,
            categories=("mon chay",),
            ingredients=("dau hu",),
        )

        results = retriever.search("nướng", filters=filters)

        self.assertEqual([result.doc_id for result in results], ["fast-vegan"])
        self.assertAlmostEqual(sum(results[0].field_scores.values()), results[0].score)

    def test_rejects_invalid_parameters_and_limit(self) -> None:
        document = make_document("recipe", title="Canh chua")

        with self.assertRaisesRegex(ValueError, "k1"):
            make_retriever([document], k1=0)
        with self.assertRaisesRegex(ValueError, "between"):
            make_retriever([document], field_b={"title": 2.0})

        retriever = make_retriever([document])
        with self.assertRaisesRegex(ValueError, "top_k"):
            retriever.search("canh", top_k=0)


if __name__ == "__main__":
    unittest.main()
