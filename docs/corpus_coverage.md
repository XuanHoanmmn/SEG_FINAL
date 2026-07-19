# Corpus scope and coverage audit

## Honest scope

SEG_FINAL is a vertical recipe search engine. It retrieves only documents that
were collected from configured public recipe sources and then included in the
current inverted index. It does not search the whole web, invent missing
recipes, or guarantee that every possible dish name is present.

The current source adapter targets public Món Ngon Mỗi Ngày recipe pages. A
two-listing-page crawl is useful for debugging but is not representative enough
for a final search demonstration.

## Build the final local corpus

Run the respectful full-listing crawl and rebuild all reproducible artifacts:

```bash
scrapy crawl mnmn -a max_pages=all -O data/raw/mnmn_recipes.jsonl
python -m src.indexing.build
```

The raw dataset, processed dataset and index remain local generated artifacts;
they are deliberately excluded from Git. The crawler continues to obey
`robots.txt`, delay, concurrency and AutoThrottle settings.

## Generate evidence of coverage

```bash
python -m src.evaluation.coverage
```

The default probes include `gà nướng`, `canh chua`, `món chay`, `hải sản`,
`phở` and `pizza`. Custom probes can be supplied repeatedly:

```bash
python -m src.evaluation.coverage \
  --query "phở" \
  --query "pizza" \
  --query "sushi"
```

On Windows CMD, put the command on one line instead of using backslashes.

`artifacts/corpus_coverage.json` records:

- exact document and vocabulary counts;
- source, category, cooking-method and difficulty distributions;
- presence/missing ratio for every important recipe field;
- whether each probe retrieved anything and its top matching documents.

This report is the defensible answer to “what does the engine cover?” because
it describes the index used in that exact run rather than relying on an
outdated estimate of the source website.

## Refresh evaluation after scaling

Stable URLs produce stable document IDs, so old human labels remain useful.
After the new index is built, run:

```bash
python -m src.evaluation.judge
python -m src.evaluation.run
```

Do not add `--rejudge`: the judging tool automatically skips existing pairs and
asks only about new candidates. Commit the updated qrels, but do not commit the
generated corpus, index or reports.
