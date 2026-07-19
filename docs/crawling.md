# Crawling policy and source notes

## Source 1: Món Ngon Mỗi Ngày

- Base URL: `https://monngonmoingay.com/`
- Listing: `https://monngonmoingay.com/tim-kiem-mon-ngon/`
- Robots: `https://monngonmoingay.com/robots.txt`
- Last manually reviewed: 2026-07-18

At review time, `robots.txt` disallowed `/wp-admin/` and exposed a sitemap. Public recipe pages were not disallowed. This is not permanent permission: Scrapy must re-check robots rules on every run.

## Safety limits

- Obey `robots.txt`.
- Use at most two concurrent requests per domain.
- Keep a delay and AutoThrottle enabled.
- Cache responses during development.
- Never bypass authentication, CAPTCHAs or blocks.
- Stop the crawl if the site begins returning repeated 403, 429 or 5xx responses.
- Store source URL and crawl time for attribution and reproducibility.
- `max_pages=all` stops at an empty/repeated listing and has a 100-listing-page
  hard limit; this protects the site and the crawler from accidental loops.

## Crawl modes

Use two listing pages only as a smoke test:

```bash
scrapy crawl mnmn -a max_pages=2 -O data/raw/mnmn_recipes.jsonl
```

That sample is intentionally too small for the final demonstration. Once its
records look correct, replace it with a full public-listing crawl:

```bash
scrapy crawl mnmn -a max_pages=all -O data/raw/mnmn_recipes.jsonl
```

Scrapy reports `item_scraped_count` when the command finishes. The source may
change over time, so use that measured count and the generated corpus report
instead of promising a fixed number of recipes.

## Extraction strategy

The extractor first checks for a standards-based JSON-LD `Recipe` object. If it is absent, it locates recipe sections by their visible Vietnamese headings: Nguyên liệu, Sơ chế, Thực hiện, Cách dùng and Mách nhỏ. This avoids binding the project to one fragile CSS class name.
