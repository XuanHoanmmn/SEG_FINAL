# TF-IDF retrieval baseline

## Scoring

The baseline uses logarithmic term frequency and smoothed inverse document frequency:

```text
tf(t, d) = 1 + log(count(t, d))
idf(t) = log((N + 1) / (df(t) + 1)) + 1
```

Term contributions are multiplied by explicit field weights before document/query normalization:

| Field | Weight |
|---|---:|
| title | 3.0 |
| ingredients | 2.0 |
| categories | 1.5 |
| cooking_method | 1.5 |
| description | 1.0 |
| instructions | 1.0 |

This baseline is intentionally kept independent from future BM25F, phrase/proximity and semantic ranking layers so their evaluation remains fair.

## Accent handling

Queries containing Vietnamese diacritics search the normalized lexicon. Fully accentless queries search the accentless lexicon generated from the same document token positions. Both paths use the same tokenizer and stopword rules as offline indexing.

## Usage

Run the preserved TF-IDF baseline explicitly (BM25F is the newer CLI default):

```bash
python -m src.query.search --ranker tfidf
```

One query:

```bash
python -m src.query.search "gà nướng" --ranker tfidf
python -m src.query.search "ga nuong" --top-k 5 --ranker tfidf
```

Machine-readable output for the later API or evaluation pipeline:

```bash
python -m src.query.search "canh chua" --ranker tfidf --json
```

Each result includes score, matched terms, matched fields and a field-level score breakdown for explainability.
