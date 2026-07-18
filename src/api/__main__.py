"""Run the local development API server."""

from __future__ import annotations

import argparse

from src.api import create_app


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the recipe search API.")
    parser.add_argument("--index", default="artifacts/inverted_index.json.gz")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=5000)
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    if not 1 <= args.port <= 65535:
        raise SystemExit("--port must be between 1 and 65535")
    app = create_app(index_path=args.index)
    app.run(host=args.host, port=args.port, debug=False)


if __name__ == "__main__":
    main()
