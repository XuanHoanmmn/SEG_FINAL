import json
import tempfile
import unittest
from pathlib import Path

from src.indexing import PositionalInvertedIndex, build_inverted_index
from src.indexing.build import build_pipeline
from src.models import RecipeDocument
from src.preprocessing import VietnameseTextProcessor, process_document


def processed_recipe(doc_id: str = "recipe-1"):
    document = RecipeDocument(
        doc_id=doc_id,
        title="Bún bò Huế",
        url=f"https://example.com/{doc_id}",
        source="example.com",
        ingredients=["Bún tươi", "thịt bò bò"],
        instructions=["Cho bún vào tô"],
        categories=["Món Huế"],
        content_hash=f"hash-{doc_id}",
    )
    processor = VietnameseTextProcessor(use_word_segmentation=False)
    return process_document(document, processor)


class PositionalInvertedIndexTests(unittest.TestCase):
    def test_stores_field_frequency_positions_and_accentless_terms(self) -> None:
        index = build_inverted_index([processed_recipe()])

        title_posting = index.get_postings("bún", field="title")[0]
        ingredient_posting = index.get_postings("bò", field="ingredients")[0]

        self.assertEqual(title_posting.positions, (0,))
        self.assertEqual(title_posting.term_frequency, 1)
        self.assertEqual(ingredient_posting.positions, (3, 4))
        self.assertEqual(ingredient_posting.term_frequency, 2)
        self.assertEqual(index.document_frequency("bún"), 1)
        self.assertEqual(index.collection_frequency("bún"), 3)
        self.assertEqual(index.document_frequency("bun", channel="accentless"), 1)

    def test_rejects_duplicate_ids_and_unknown_channels(self) -> None:
        recipe = processed_recipe()
        index = PositionalInvertedIndex()
        index.add_document(recipe)

        with self.assertRaisesRegex(ValueError, "Duplicate"):
            index.add_document(recipe)
        with self.assertRaisesRegex(ValueError, "channel"):
            index.get_postings("bún", channel="invalid")

    def test_gzip_round_trip_preserves_postings(self) -> None:
        index = build_inverted_index([processed_recipe()])

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "index.json.gz"
            index.save(path)
            loaded = PositionalInvertedIndex.load(path)

        self.assertEqual(loaded.statistics(), index.statistics())
        self.assertEqual(
            loaded.get_postings("hue", channel="accentless"),
            index.get_postings("hue", channel="accentless"),
        )

    def test_build_pipeline_writes_all_reproducible_artifacts(self) -> None:
        first = processed_recipe("recipe-1").document
        second = processed_recipe("recipe-2").document
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raw = root / "raw.jsonl"
            processed = root / "processed.jsonl"
            index_path = root / "index.json.gz"
            report_path = root / "report.json"
            raw.write_text(
                "\n".join(json.dumps(value, ensure_ascii=False) for value in [first, second]),
                encoding="utf-8",
            )

            report = build_pipeline(
                raw,
                processed,
                index_path,
                report_path,
                use_word_segmentation=False,
            )
            loaded = PositionalInvertedIndex.load(index_path)
            saved_report = json.loads(report_path.read_text(encoding="utf-8"))

        self.assertEqual(report["processing"]["output_records"], 2)
        self.assertEqual(report["index"]["document_count"], 2)
        self.assertEqual(len(loaded), 2)
        self.assertEqual(saved_report, report)


if __name__ == "__main__":
    unittest.main()
