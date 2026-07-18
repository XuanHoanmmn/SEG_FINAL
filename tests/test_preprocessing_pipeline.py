import json
import tempfile
import unittest
from pathlib import Path

from src.models import RecipeDocument
from src.preprocessing import (
    VietnameseTextProcessor,
    iter_processed_jsonl,
    process_document,
    process_jsonl,
)


def make_recipe(doc_id: str = "recipe-1", content_hash: str = "hash-1") -> RecipeDocument:
    return RecipeDocument(
        doc_id=doc_id,
        title="Bún Bò Huế",
        url=f"https://example.com/{doc_id}",
        source="example.com",
        description="Đậm đà và dễ làm",
        ingredients=["Bún tươi", "Thịt bò"],
        instructions=["Cho bún vào tô."],
        categories=["Món Huế"],
        cooking_method="nấu",
        content_hash=content_hash,
    )


class VietnameseTextProcessorTests(unittest.TestCase):
    def test_process_document_preserves_source_and_builds_search_forms(self) -> None:
        processor = VietnameseTextProcessor(
            use_word_segmentation=False,
            stopwords={"và"},
        )

        processed = process_document(make_recipe(), processor)

        self.assertEqual(processed.document["title"], "Bún Bò Huế")
        self.assertEqual(processed.normalized_fields["title"], "bún bò huế")
        self.assertEqual(processed.tokens["title"], ["bún", "bò", "huế"])
        self.assertEqual(processed.accentless_tokens["title"], ["bun", "bo", "hue"])
        self.assertNotIn("và", processed.ranking_tokens["description"])

    def test_custom_segmenter_keeps_multiword_terms_together(self) -> None:
        processor = VietnameseTextProcessor(
            segmenter=lambda _: ["bún bò", "Huế"],
            stopwords=set(),
        )

        self.assertEqual(processor.tokenize("Bún bò Huế"), ["bún_bò", "huế"])

    def test_process_jsonl_reports_invalid_and_duplicate_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            raw_path = Path(directory) / "raw.jsonl"
            processed_path = Path(directory) / "processed.jsonl"
            record = make_recipe().to_dict()
            raw_path.write_text(
                "\n".join(
                    [
                        json.dumps(record, ensure_ascii=False),
                        json.dumps(record, ensure_ascii=False),
                        "{invalid json}",
                    ]
                ),
                encoding="utf-8",
            )

            report = process_jsonl(
                raw_path,
                processed_path,
                VietnameseTextProcessor(use_word_segmentation=False),
            )
            recipes = list(iter_processed_jsonl(processed_path))

        self.assertEqual(report.input_records, 3)
        self.assertEqual(report.output_records, 1)
        self.assertEqual(report.duplicate_records, 1)
        self.assertEqual(report.invalid_records, 1)
        self.assertEqual(recipes[0].doc_id, "recipe-1")


if __name__ == "__main__":
    unittest.main()
