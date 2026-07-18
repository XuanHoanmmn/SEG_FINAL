# Data quality and domain query expansion

## Why this phase exists

The source page mixes recipe content with interface labels and SEO recommendation
text. Examples observed during human relevance judging include standalone
`Muỗng`/`Gram` entries and descriptions beginning with `Gợi ý cơm nhà 3 món`.
Indexing those strings introduces false matches and makes ranking explanations
harder to trust.

## Conservative cleanup

Cleanup runs while converting raw JSONL into processed JSONL. The raw crawl is
never modified, so every transformation is reproducible and auditable.

Current rules:

- remove standalone ingredient UI labels `Muỗng` and `Gram`;
- preserve those words when they occur inside a real ingredient measurement;
- clear descriptions that are recommendation blocks rather than descriptions of
  the current recipe;
- preserve source categories because they may be legitimate site metadata.

`artifacts/index_report.json` records `cleaned_records`,
`ingredient_artifacts_removed`, and `promotional_descriptions_cleared`.

## Weighted query expansion

The TF-IDF model remains a literal lexical baseline. The advanced BM25F pipeline
adds a transparent domain expansion for the umbrella concept `hải sản`:

```text
hải sản -> cá, tôm, mực, nghêu, ốc
```

Expanded terms receive weight `0.35`; original user terms keep weight `1.0`.
Exact phrase and proximity boosts use only original terms. Search results expose
the expansion in `expanded_terms`, and the CLI prints it for explainability.

This design solves a vocabulary mismatch without embeddings, external APIs, or
hidden rules. The synonym map is deliberately small and reviewable.

## Rebuild and compare

```bash
python -m src.indexing.build
python -m src.query.search "hải sản"
python -m src.evaluation.run
```

Compare the new report with the Phase 6 baseline. The same committed human qrels
are reused, so improvements reflect code/data changes rather than relabeling.
