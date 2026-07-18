# SEG_FINAL development guidance

## Project goal

Build a vertical search engine for Vietnamese recipes. The backend search logic is the current priority; do not add a frontend until the retrieval and evaluation milestones are complete.

## Required commands

```bash
python -m unittest discover -s tests -v
python -m pytest
python -m ruff check .
```

## Engineering rules

- Keep crawler, preprocessing, indexing, retrieval, ranking, API, and evaluation code in separate modules.
- Preserve the original document text and create normalized search fields separately.
- Implement and retain a TF-IDF baseline before adding BM25F or semantic retrieval.
- The inverted index must be implemented in this repository and store document IDs, term frequency, field, and token positions.
- Every ranking or preprocessing change must include tests.
- Do not commit crawled datasets, generated indexes, model files, secrets, or virtual environments.
- Do not bypass robots.txt, CAPTCHAs, authentication, or website rate limits.
