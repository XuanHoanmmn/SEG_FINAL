# Preprocessing and positional inverted index

## Generated artifacts

- `data/processed/recipes.jsonl`: original records plus normalized field text, Vietnamese tokens, accentless tokens and stopword-filtered ranking tokens.
- `artifacts/inverted_index.json.gz`: custom field-aware positional inverted index.
- `artifacts/index_report.json`: input/output quality counters and index statistics.

Generated files are reproducible and intentionally ignored by Git.

## Indexed fields

The index keeps independent token streams for `title`, `description`, `ingredients`, `instructions`, `categories` and `cooking_method`. Every posting stores a document ID, field, term frequency and ordered token positions.

Two lexicons are built:

1. `normalized` preserves Vietnamese accents for precise matching.
2. `accentless` supports queries typed without Vietnamese diacritics.

Source text is never overwritten. Stopwords are retained in the positional index so future phrase queries remain correct; a separate stopword-filtered token stream is prepared for ranking.

## Build command

Run from the repository root after crawling:

```bash
python -m src.indexing.build
```

The command validates raw records, removes duplicate IDs/content hashes, writes processed JSONL atomically, builds the compressed index and prints a quality report. Word segmentation uses `underthesea` when installed and falls back to the deterministic Unicode tokenizer otherwise.
