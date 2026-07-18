import unittest

from src.preprocessing import VietnameseTextProcessor
from src.query import QueryProcessor


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


if __name__ == "__main__":
    unittest.main()
