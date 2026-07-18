import unittest

from src.models import RecipeDocument


class RecipeDocumentTests(unittest.TestCase):
    def test_document_calculates_total_time_and_searchable_text(self) -> None:
        document = RecipeDocument(
            doc_id="recipe-1",
            title="Gà nướng sả",
            url="https://example.com/ga-nuong-sa",
            source="example",
            ingredients=["gà", "sả"],
            instructions=["Ướp gà", "Nướng chín"],
            prep_time_minutes=15,
            cook_time_minutes=35,
        )

        self.assertEqual(document.total_time_minutes, 50)
        self.assertIn("Gà nướng sả", document.searchable_text())
        self.assertIn("sả", document.searchable_text())
        self.assertEqual(document.to_dict()["total_time_minutes"], 50)

    def test_document_rejects_missing_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, "title"):
            RecipeDocument(doc_id="1", title=" ", url="https://example.com", source="example")

    def test_document_rejects_negative_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "cook_time_minutes"):
            RecipeDocument(
                doc_id="1",
                title="Test recipe",
                url="https://example.com",
                source="example",
                cook_time_minutes=-1,
            )


if __name__ == "__main__":
    unittest.main()
