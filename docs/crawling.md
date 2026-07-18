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

## Extraction strategy

The extractor first checks for a standards-based JSON-LD `Recipe` object. If it is absent, it locates recipe sections by their visible Vietnamese headings: Nguyên liệu, Sơ chế, Thực hiện, Cách dùng and Mách nhỏ. This avoids binding the project to one fragile CSS class name.

