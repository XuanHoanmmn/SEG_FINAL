"""Flask application factory and versioned search endpoints."""

from __future__ import annotations

from dataclasses import dataclass
from http import HTTPStatus
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, render_template, request
from werkzeug.exceptions import HTTPException

from src.api.service import SearchService
from src.indexing import PositionalInvertedIndex
from src.query import SearchFilters

API_VERSION = "1.0"
DEFAULT_INDEX_PATH = "artifacts/inverted_index.json.gz"
MAX_PAGE_SIZE = 50


@dataclass(frozen=True, slots=True)
class APIError(Exception):
    """Expected client error rendered in one stable JSON shape."""

    code: str
    message: str
    status: int = HTTPStatus.BAD_REQUEST
    details: dict[str, Any] | None = None


def _integer_parameter(name: str, default: int, *, minimum: int) -> int:
    raw_value = request.args.get(name)
    if raw_value in (None, ""):
        return default
    try:
        value = int(raw_value)
    except ValueError as exc:
        raise APIError(
            "invalid_parameter",
            f"'{name}' must be an integer.",
            details={"parameter": name},
        ) from exc
    if value < minimum:
        raise APIError(
            "invalid_parameter",
            f"'{name}' must be at least {minimum}.",
            details={"parameter": name},
        )
    return value


def _parse_filters() -> SearchFilters:
    max_time_raw = request.args.get("max_time")
    max_time = None
    if max_time_raw not in (None, ""):
        max_time = _integer_parameter("max_time", 0, minimum=0)
    try:
        return SearchFilters(
            max_time_minutes=max_time,
            difficulty=request.args.get("difficulty") or None,
            categories=tuple(request.args.getlist("category")),
            ingredients=tuple(request.args.getlist("ingredient")),
            cooking_methods=tuple(request.args.getlist("method")),
        )
    except ValueError as exc:
        raise APIError("invalid_filter", str(exc)) from exc


def create_app(
    *,
    index: PositionalInvertedIndex | None = None,
    index_path: str | Path = DEFAULT_INDEX_PATH,
) -> Flask:
    """Create an API app with a preloaded reusable search service."""

    app = Flask(__name__)
    if index is None:
        path = Path(index_path)
        if not path.exists():
            raise FileNotFoundError(
                f"Index not found: {path}. Run `python -m src.indexing.build` first."
            )
        index = PositionalInvertedIndex.load(path)
    service = SearchService(index)
    app.extensions["search_service"] = service

    @app.after_request
    def add_response_headers(response):
        response.headers["X-API-Version"] = API_VERSION
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    @app.get("/")
    def home_page():
        """Render the search landing page."""

        statistics = service.index.statistics().to_dict()
        return render_template(
            "home.html",
            document_count=statistics["document_count"],
            vocabulary_size=statistics["normalized_vocabulary_size"],
        )

    @app.get("/search")
    def search_page():
        """Render the browser search client; results are loaded from API v1."""

        query = " ".join((request.args.get("q") or "").split())
        return render_template("search.html", initial_query=query)

    @app.get("/api/v1")
    def api_root():
        return jsonify(
            {
                "name": "SEG_FINAL Vietnamese Recipe Search API",
                "version": API_VERSION,
                "endpoints": ["/api/v1/health", "/api/v1/search"],
                "web": ["/", "/search"],
            }
        )

    @app.get("/api/v1/health")
    def health():
        statistics = service.index.statistics().to_dict()
        return jsonify(
            {
                "status": "ok",
                "api_version": API_VERSION,
                "index": statistics,
                "rankers": sorted(service.rankers),
            }
        )

    @app.get("/api/v1/search")
    def search():
        query = " ".join((request.args.get("q") or "").split())
        if not query:
            raise APIError(
                "missing_query",
                "Query parameter 'q' is required.",
                details={"parameter": "q"},
            )
        ranker = (request.args.get("ranker") or "bm25f").casefold()
        if ranker not in service.rankers:
            raise APIError(
                "invalid_ranker",
                "'ranker' must be either 'bm25f' or 'tfidf'.",
                details={"parameter": "ranker"},
            )
        page = _integer_parameter("page", 1, minimum=1)
        page_size = _integer_parameter("page_size", 10, minimum=1)
        if page_size > MAX_PAGE_SIZE:
            raise APIError(
                "invalid_parameter",
                f"'page_size' cannot exceed {MAX_PAGE_SIZE}.",
                details={"parameter": "page_size"},
            )
        return jsonify(
            service.search(
                query,
                ranker_name=ranker,
                page=page,
                page_size=page_size,
                filters=_parse_filters(),
            )
        )

    @app.errorhandler(APIError)
    def handle_api_error(error: APIError):
        payload: dict[str, Any] = {"error": {"code": error.code, "message": error.message}}
        if error.details:
            payload["error"]["details"] = error.details
        return jsonify(payload), error.status

    @app.errorhandler(HTTPException)
    def handle_http_error(error: HTTPException):
        return (
            jsonify(
                {
                    "error": {
                        "code": error.name.lower().replace(" ", "_"),
                        "message": error.description,
                    }
                }
            ),
            error.code,
        )

    return app
