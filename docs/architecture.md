# Backend architecture

## Offline pipeline

1. The crawler saves one raw JSON object per recipe without altering source text.
2. The preprocessing pipeline validates fields, removes duplicates and creates normalized search forms.
3. The index builder creates a field-aware inverted index containing document ID, term frequency and token positions.
4. A TF-IDF baseline is built first and kept for evaluation.
5. BM25F, phrase/proximity boosts and optional semantic vectors are added as independent layers.

## Online pipeline

1. The query processor applies the same normalization rules used for documents.
2. Filters are parsed separately from free text.
3. Lexical retrieval produces candidates from the inverted index.
4. Optional semantic retrieval produces a second candidate list.
5. Ranking combines candidates, applies boosts and returns an explanation.
6. The API adds snippets, highlights, pagination and latency metadata.

## Storage decisions

- Raw and processed records: JSONL for reproducibility and inspection.
- Document metadata and filters: SQLite.
- Lexicon and postings: custom project artifacts loaded into memory for search.
- Embeddings: normalized NumPy matrix, only after the lexical baseline is complete.

## Evaluation

The project will compare TF-IDF, BM25F, Vietnamese query enhancements and hybrid retrieval using the same judged query set. Required metrics are Precision@10 and MAP; additional metrics are Recall@20, MRR@10, nDCG@10 and p50/p95 latency.

