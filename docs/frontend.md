# Search Web Interface

## Scope

The web interface is served by the same Flask application as API v1. This keeps
the demonstration deployment small and avoids a second frontend service or
cross-origin configuration.

Routes:

- `/` renders the landing page and current index statistics;
- `/search?q=...` renders the search client shell;
- `/api/v1/search` remains the only source of dynamic result data.

## User experience

The result client supports BM25F/TF-IDF selection, maximum-time, difficulty,
category and cooking-method filters, pagination, score explanations and mobile
filter navigation. State is reflected in the URL so a filtered result page can
be refreshed or shared.

Loading skeletons avoid layout jumps. Dedicated empty, no-query and connection
error panels make each system state explicit. The layout adapts to desktop,
tablet and mobile widths without external CSS or JavaScript dependencies.

## Safe rendering

The API returns snippet text and structured highlight ranges rather than HTML.
The browser client appends text nodes and `mark` elements for those ranges.
Titles, categories, explanations and filter labels use `textContent`. External
recipe and image URLs are accepted only when their protocol is HTTP or HTTPS.

## Local run

Build the index and start Flask:

```bash
python -m src.indexing.build
python -m src.api
```

Then open `http://127.0.0.1:5000/`.
