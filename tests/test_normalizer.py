import unittest

from src.preprocessing.normalizer import (
    build_search_forms,
    normalize_text,
    normalize_unicode,
    strip_accents,
    tokenize_basic,
)


class NormalizerTests(unittest.TestCase):
    def test_normalize_text_preserves_vietnamese_and_collapses_whitespace(self) -> None:
        self.assertEqual(normalize_text("  GÀ\n nướng   SẢ  "), "gà nướng sả")

    def test_strip_accents_handles_vietnamese_d(self) -> None:
        self.assertEqual(strip_accents("Đậu hũ chiên"), "Dau hu chien")
        self.assertEqual(strip_accents("đường"), "duong")

    def test_build_search_forms_supports_accentless_queries(self) -> None:
        forms = build_search_forms("Bún bò Huế")

        self.assertEqual(forms["normalized"], "bún bò huế")
        self.assertEqual(forms["accentless"], "bun bo hue")

    def test_tokenize_basic_returns_unicode_words_and_numbers(self) -> None:
        self.assertEqual(tokenize_basic("Gà nướng 30 phút!"), ["gà", "nướng", "30", "phút"])

    def test_normalize_unicode_rejects_unknown_form(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported"):
            normalize_unicode("text", "UNKNOWN")


if __name__ == "__main__":
    unittest.main()
