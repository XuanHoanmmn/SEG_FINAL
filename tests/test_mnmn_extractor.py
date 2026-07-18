import json
import unittest
from pathlib import Path

from src.crawler.extractors.mon_ngon_moi_ngay import NotRecipePage, extract_recipe

FIXTURE_DIR = Path(__file__).parent / "fixtures"


class MonNgonMoiNgayExtractorTests(unittest.TestCase):
    def test_extracts_semantic_dom_recipe_and_removes_duplicates(self) -> None:
        html_text = (FIXTURE_DIR / "mnmn_recipe.html").read_text(encoding="utf-8")

        document = extract_recipe(
            html_text,
            "https://monngonmoingay.com/ga-nuong-chanh-sa-mayo/?tracking=1",
        )

        self.assertEqual(document.title, "Gà Nướng Chanh Sả Mayo")
        self.assertEqual(len(document.ingredients), 3)
        self.assertIn("Má đùi gà 250g", document.ingredients)
        self.assertEqual(len(document.instructions), 4)
        self.assertEqual(document.cook_time_minutes, 20)
        self.assertEqual(document.servings, "4 người")
        self.assertEqual(document.difficulty, "Dễ")
        self.assertNotIn("Thông tin dinh dưỡng", document.difficulty)
        self.assertEqual(document.cooking_method, "nướng")
        self.assertEqual(document.categories, ["Nướng"])
        self.assertEqual(document.url, "https://monngonmoingay.com/ga-nuong-chanh-sa-mayo")
        self.assertTrue(document.content_hash)

    def test_prefers_jsonld_recipe_when_available(self) -> None:
        recipe = {
            "@context": "https://schema.org",
            "@type": "Recipe",
            "name": "Canh chua cá",
            "description": "Món canh chua miền Nam.",
            "recipeIngredient": ["Cá", "Cà chua"],
            "recipeInstructions": [
                {"@type": "HowToStep", "text": "Sơ chế cá."},
                {"@type": "HowToStep", "text": "Nấu canh."},
            ],
            "prepTime": "PT15M",
            "cookTime": "PT30M",
            "recipeYield": "4 người",
            "recipeCategory": ["Canh", "Món Việt"],
        }
        html_text = (
            "<html><head><script type='application/ld+json'>"
            + json.dumps(recipe, ensure_ascii=False)
            + "</script></head><body></body></html>"
        )

        document = extract_recipe(html_text, "https://monngonmoingay.com/canh-chua-ca/")

        self.assertEqual(document.title, "Canh chua cá")
        self.assertEqual(document.prep_time_minutes, 15)
        self.assertEqual(document.cook_time_minutes, 30)
        self.assertEqual(document.categories, ["Canh", "Món Việt"])

    def test_rejects_non_recipe_page(self) -> None:
        with self.assertRaises(NotRecipePage):
            extract_recipe("<html><h1>Giới thiệu</h1></html>", "https://example.com/about")


if __name__ == "__main__":
    unittest.main()
