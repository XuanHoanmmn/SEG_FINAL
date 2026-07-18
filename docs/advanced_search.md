# BM25F, phrase proximity and structured filters

## BM25F

BM25F combines term frequency from independent fields after field-specific length normalization. Short fields such as `title` and `categories` use lower `b` values, while long descriptions and instructions use stronger length normalization.

```text
normalized_tf(field) = tf / ((1 - b_field) + b_field * field_length / average_field_length)
combined_tf = sum(field_weight * normalized_tf(field))
idf = log(1 + (N - df + 0.5) / (df + 0.5))
score = idf * (k1 + 1) * combined_tf / (k1 + combined_tf)
```

Defaults: `k1=1.2`, title weight `3.0`, ingredients `2.0`, categories/cooking method `1.5`, and description/instructions `1.0`.

## Phrase and proximity evidence

For queries with at least two terms, the retriever reads positional postings inside each field:

- An exact ordered phrase receives a strong boost.
- Terms in the same field receive a smaller proximity boost that decreases as the minimum gap grows.
- Terms located in different fields do not receive an artificial phrase boost.

This allows `gà nướng` to rank a document containing the exact phrase above a document containing `nướng ... gà`, while both documents still receive lexical BM25F scores.

## Filters

Filters are accent-insensitive and are applied before scoring:

```bash
python -m src.query.search "gà" --max-time 15 --difficulty "Dễ"
python -m src.query.search "nướng" --category "Món chay"
python -m src.query.search "món ngon" --ingredient "đậu hũ" --method "nướng"
```

Repeat `--category` or `--ingredient` to require multiple values. `--method` accepts one or more alternative cooking methods.

## Baseline comparison

BM25F is now the CLI default. The required TF-IDF baseline remains available unchanged:

```bash
python -m src.query.search "gà nướng" --ranker bm25f
python -m src.query.search "gà nướng" --ranker tfidf
```

Both rankers return the same result schema, enabling later offline evaluation with the same query judgments.
