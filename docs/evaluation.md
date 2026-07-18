# Offline retrieval evaluation

## Why human judgments are required

Search scores cannot be reused as ground truth because that would reward the same ranking logic being evaluated. Phase 6 therefore pools candidates from both TF-IDF and BM25F, then asks a human to assign independent graded relevance labels.

The repository contains 20 stable queries in `data/ground_truth/queries.jsonl`. They cover accented and accentless text, ingredients, cooking methods, meal categories and structured constraints.

## Step 1: judge the pooled candidates

```bash
python -m src.evaluation.judge
```

For every candidate, enter:

- `0`: irrelevant to the query intent
- `1`: relevant, but not the most direct answer
- `2`: highly relevant and directly satisfies the intent
- `s`: skip for now
- `q`: save and quit

The command saves `data/ground_truth/qrels.jsonl` after every label. Running it again resumes automatically. Use `--query-id q02` to judge one query or `--rejudge` to replace previous labels.

The default pool depth is five results from each ranker. If both rankers return
no candidate for a known vocabulary gap such as `hải sản`, the judging command
uses a documented seafood-term expansion only to construct the human pool. The
evaluation runner still executes the original query, preserving an honest zero
when a model cannot retrieve it.

If a query has candidates but no relevant document in the first pool, increase
the pool depth:

```bash
python -m src.evaluation.judge --query-id q19 --pool-depth 10
```

## Step 2: run the experiment

After all 20 queries have at least one positive label:

```bash
python -m src.evaluation.run
```

The runner executes both models on the same queries, filters and qrels. It reports:

- Precision@10
- MAP (mean average precision)
- Recall@20
- MRR@10
- nDCG@10 with graded relevance
- p50 and p95 query latency

Outputs:

- `artifacts/evaluation_report.json`: complete summaries, per-query values, top document IDs and BM25F-minus-TF-IDF deltas.
- `artifacts/evaluation_results.csv`: Excel-friendly per-query table encoded with a UTF-8 BOM.

Artifacts are generated and ignored by Git. The completed `qrels.jsonl` is source evaluation data and should be committed or submitted with the project for reproducibility.

## Methodology note

Unjudged documents are treated as irrelevant, which is the normal limitation of pooled evaluation. Use the union of both rankers and increase pool depth when necessary to reduce pooling bias. Do not tune BM25F on the final judged set and then report the same set as an unbiased test; if enough judgments are available, reserve some queries for final testing.
