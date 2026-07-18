import unittest

from src.indexing import build_inverted_index
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document
from src.query import QueryProcessor, SearchFilters
from src.retrieval import TfidfRetriever


def make_document(
    doc_id: str,
    *,
    title: str,
    description: str = "",
    ingredients: list[str] | None = None,
    instructions: list[str] | None = None,
) -> RecipeDocument:
    return RecipeDocument(
        doc_id=doc_id,
        title=title,
        url=f"https://example.com/{doc_id}",
        source="example.com",
        description=description,
        ingredients=ingredients or ["nước"],
        instructions=instructions or ["chuẩn bị món ăn"],
        content_hash=f"hash-{doc_id}",
    )


def make_retriever(documents: list[RecipeDocument]) -> TfidfRetriever:
    text_processor = VietnameseTextProcessor(use_word_segmentation=False)
    recipes = [process_document(document, text_processor) for document in documents]
    index = build_inverted_index(recipes)
    return TfidfRetriever(
        index,
        query_processor=QueryProcessor(text_processor),
    )


class TfidfRetrieverTests(unittest.TestCase):
    def test_ranks_title_match_above_description_match(self) -> None:
        retriever = make_retriever(
            [
                make_document("title-match", title="Gà", description="món"),
                make_document("description-match", title="Món", description="gà"),
            ]
        )

        results = retriever.search("gà")

        self.assertEqual(
            [result.doc_id for result in results],
            ["title-match", "description-match"],
        )
        self.assertGreater(results[0].score, results[1].score)
        self.assertEqual(results[0].matched_fields, ("title",))

    def test_accented_and_accentless_queries_rank_the_same_recipe_first(self) -> None:
        retriever = make_retriever(
            [
                make_document(
                    "grilled-chicken",
                    title="Gà nướng mật ong",
                    ingredients=["gà", "mật ong"],
                    instructions=["nướng gà đến khi vàng"],
                ),
                make_document("salad", title="Salad rau củ"),
            ]
        )

        accented = retriever.search("gà nướng")
        accentless = retriever.search("ga nuong")

        self.assertEqual(accented[0].doc_id, "grilled-chicken")
        self.assertEqual(accentless[0].doc_id, "grilled-chicken")
        self.assertAlmostEqual(accented[0].score, accentless[0].score)

    def test_result_contains_explainable_field_breakdown(self) -> None:
        retriever = make_retriever(
            [make_document("recipe", title="Canh chua cá", ingredients=["cá", "me chua"])]
        )

        result = retriever.search("cá")[0]

        self.assertEqual(result.matched_terms, ("cá",))
        self.assertEqual(result.matched_fields, ("ingredients", "title"))
        self.assertAlmostEqual(sum(result.field_scores.values()), result.score)
        self.assertEqual(result.to_dict()["matched_terms"], ["cá"])

    def test_handles_empty_unknown_and_invalid_limit(self) -> None:
        retriever = make_retriever([make_document("recipe", title="Canh chua")])

        self.assertEqual(retriever.search(""), [])
        self.assertEqual(retriever.search("pizza"), [])
        with self.assertRaisesRegex(ValueError, "top_k"):
            retriever.search("canh", top_k=0)

    def test_applies_shared_filters(self) -> None:
        fast = make_document("fast", title="Canh chua")
        slow = make_document("slow", title="Canh chua cá")
        fast.cook_time_minutes = 10
        slow.cook_time_minutes = 60
        retriever = make_retriever([fast, slow])

        results = retriever.search("canh", filters=SearchFilters(max_time_minutes=15))

        self.assertEqual([result.doc_id for result in results], ["fast"])


if __name__ == "__main__":
    unittest.main()
