import unittest

from src.models import RecipeDocument
from src.preprocessing import sanitize_recipe_document


class DataQualityTests(unittest.TestCase):
    def test_removes_ui_units_and_promotional_recommendation_description(self) -> None:
        document = RecipeDocument(
            doc_id="recipe",
            title="Gà nướng",
            url="https://example.com/recipe",
            source="example.com",
            description="Gợi ý cơm nhà 3 món: Gà nướng – Canh – Salad",
            ingredients=["Muỗng", "Gram", "Thịt gà 250g", "Mật ong 1M"],
            instructions=["Nướng gà"],
        )

        cleaned, changes = sanitize_recipe_document(document)

        self.assertEqual(cleaned.ingredients, ["Thịt gà 250g", "Mật ong 1M"])
        self.assertEqual(cleaned.description, "")
        self.assertEqual(changes.ingredient_artifacts_removed, 2)
        self.assertEqual(changes.promotional_descriptions_cleared, 1)
        self.assertTrue(changes.changed)

    def test_preserves_legitimate_measurements_inside_ingredient_lines(self) -> None:
        document = RecipeDocument(
            doc_id="recipe",
            title="Canh",
            url="https://example.com/recipe",
            source="example.com",
            description="Món canh thanh mát.",
            ingredients=["Cá 200 gram", "Nước mắm 1 muỗng"],
            instructions=["Nấu canh"],
        )

        cleaned, changes = sanitize_recipe_document(document)

        self.assertIs(cleaned, document)
        self.assertFalse(changes.changed)


if __name__ == "__main__":
    unittest.main()
