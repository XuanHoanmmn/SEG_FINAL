import unittest

from src.preprocessing import VietnameseTextProcessor
from src.query import QueryProcessor, VietnameseRecipeQueryExpander


class QueryProcessorTests(unittest.TestCase):
    def setUp(self) -> None:
        text_processor = VietnameseTextProcessor(use_word_segmentation=False)
        self.processor = QueryProcessor(text_processor)

    def test_selects_normalized_channel_for_accented_query(self) -> None:
        query = self.processor.process("  Gà   nướng  ")

        self.assertEqual(query.normalized, "gà nướng")
        self.assertEqual(query.channel, "normalized")
        self.assertEqual(query.terms, ("gà", "nướng"))

    def test_selects_accentless_channel_for_unaccented_query(self) -> None:
        query = self.processor.process("Ga nuong")

        self.assertEqual(query.channel, "accentless")
        self.assertEqual(query.terms, ("ga", "nuong"))

    def test_keeps_stopwords_when_query_contains_only_stopwords(self) -> None:
        query = self.processor.process("và với")

        self.assertEqual(query.terms, ("và", "với"))
        self.assertEqual(query.term_frequencies["và"], 1)

    def test_empty_query_has_no_terms(self) -> None:
        self.assertEqual(self.processor.process("   ").terms, ())

    def test_expands_recipe_concept_with_lower_weight(self) -> None:
        processor = QueryProcessor(
            VietnameseTextProcessor(use_word_segmentation=False),
            query_expander=VietnameseRecipeQueryExpander(),
        )

        query = processor.process("món hải sản")

        self.assertEqual(query.terms, ("món", "hải", "sản"))
        self.assertEqual(query.expanded_terms, ("cá", "tôm", "mực", "nghêu", "ốc"))
        self.assertEqual(query.term_boost("hải"), 1.0)
        self.assertEqual(query.term_boost("mực"), 0.35)

    def test_expands_accentless_query_into_accentless_terms(self) -> None:
        processor = QueryProcessor(
            VietnameseTextProcessor(use_word_segmentation=False),
            query_expander=VietnameseRecipeQueryExpander(),
        )

        query = processor.process("hai san")

        self.assertEqual(query.channel, "accentless")
        self.assertEqual(query.expanded_terms, ("ca", "tom", "muc", "ngheu", "oc"))


if __name__ == "__main__":
    unittest.main()
