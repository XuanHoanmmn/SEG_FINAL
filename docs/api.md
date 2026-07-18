# Search API

## Run locally

Build the index once, then start the Flask development server:

```bash
python -m src.indexing.build
python -m src.api
```

The default address is `http://127.0.0.1:5000`. The index is loaded once at
startup and both rankers are reused for later requests.

## Health

```http
GET /api/v1/health
```

The response includes the API version, enabled rankers and current index
statistics. It can be used as a readiness check before connecting a frontend.

## Search

```http
GET /api/v1/search?q=gà+nướng&page=1&page_size=10&ranker=bm25f
```

Parameters:

- `q`: required query text;
- `ranker`: `bm25f` (default) or `tfidf`;
- `page`: one-based page number, default `1`;
- `page_size`: default `10`, maximum `50`;
- `max_time`: maximum recipe time in minutes;
- `difficulty`: exact accent-insensitive difficulty;
- `category`: repeatable category filter;
- `ingredient`: repeatable ingredient filter;
- `method`: repeatable cooking-method filter.

Example with repeated filters:

```text
/api/v1/search?q=nướng&category=Món%20mặn&ingredient=gà&method=nướng
```

## Response design

The response contains:

- normalized query, ranker, filters and transparent expanded terms;
- pagination metadata and total matched results;
- facets computed over the complete filtered result set;
- compact recipe metadata;
- a safe snippet with structured highlight offsets;
- matched terms, fields and per-field score contributions;
- server-side search time in milliseconds.

Highlights are ranges in the returned snippet text:

```json
{
  "field": "title",
  "text": "Gà nướng mật ong",
  "highlights": [
    {"start": 0, "end": 2, "term": "gà"},
    {"start": 3, "end": 8, "term": "nướng"}
  ]
}
```

The API intentionally does not return prebuilt HTML. A frontend should escape
the snippet text, then apply highlight ranges in order.

## Errors

Client and routing errors use one stable JSON shape:

```json
{
  "error": {
    "code": "invalid_parameter",
    "message": "'page' must be an integer.",
    "details": {"parameter": "page"}
  }
}
```

The Flask server is for local development and demonstrations. Use a production
WSGI server when deploying publicly.
