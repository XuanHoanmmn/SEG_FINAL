# Ground truth

- `queries.jsonl` contains 20 stable Vietnamese information needs, including accented, accentless and filtered queries.
- `qrels.jsonl` is created by the interactive judging command and stores human labels for query-document pairs.

Relevance scale:

- `0`: irrelevant
- `1`: relevant
- `2`: highly relevant / directly satisfies the intent

Do not infer qrels from ranking scores. Human judgments are required so TF-IDF and BM25F are evaluated independently of the systems that generated the candidate pool.
