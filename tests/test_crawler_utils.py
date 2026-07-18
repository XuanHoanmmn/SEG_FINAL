import unittest

from src.crawler.utils import (
    canonicalize_url,
    deduplicate_texts,
    make_document_id,
    parse_duration_minutes,
)


class CrawlerUtilsTests(unittest.TestCase):
    def test_parse_duration_minutes_supports_iso_and_vietnamese(self) -> None:
        self.assertEqual(parse_duration_minutes("PT1H15M"), 75)
        self.assertEqual(parse_duration_minutes("1 giờ 20 phút"), 80)
        self.assertEqual(parse_duration_minutes("30 Phút"), 30)
        self.assertIsNone(parse_duration_minutes("không rõ"))

    def test_canonical_url_and_document_id_are_stable(self) -> None:
        first = canonicalize_url("HTTPS://Example.com/recipe/?utm_source=test#top")
        second = canonicalize_url("https://example.com/recipe")

        self.assertEqual(first, "https://example.com/recipe")
        self.assertEqual(first, second)
        self.assertEqual(make_document_id(first), make_document_id(second))

    def test_deduplicate_texts_preserves_order(self) -> None:
        values = deduplicate_texts([" Gà ", "sả", "gà", "", "Sả"])
        self.assertEqual(values, ["Gà", "sả"])


if __name__ == "__main__":
    unittest.main()

