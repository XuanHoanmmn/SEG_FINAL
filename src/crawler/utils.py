"""Small deterministic helpers for crawler records."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from urllib.parse import urlsplit, urlunsplit

from src.preprocessing.normalizer import normalize_text

_ISO_DURATION_RE = re.compile(
    r"^P(?:\d+D)?(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?:\d+)S)?)?$",
    flags=re.IGNORECASE,
)
_HOURS_RE = re.compile(r"(?P<hours>\d+)\s*(?:giờ|gio|h)\b", flags=re.IGNORECASE)
_MINUTES_RE = re.compile(r"(?P<minutes>\d+)\s*(?:phút|phut|p)\b", flags=re.IGNORECASE)


def canonicalize_url(url: str) -> str:
    """Remove fragments and query parameters from a recipe URL."""

    parts = urlsplit(url.strip())
    path = parts.path or "/"
    if path != "/":
        path = f"{path.rstrip('/')}"
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, "", ""))


def make_document_id(url: str, *, prefix: str = "mnmn") -> str:
    """Create a stable compact document ID from the canonical source URL."""

    digest = hashlib.sha256(canonicalize_url(url).encode("utf-8")).hexdigest()[:16]
    return f"{prefix}-{digest}"


def make_content_hash(*values: object) -> str:
    """Hash normalized content so duplicated recipes can be detected."""

    payload = json.dumps(values, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(normalize_text(payload).encode("utf-8")).hexdigest()


def deduplicate_texts(values: Iterable[str]) -> list[str]:
    """Remove blank and repeated strings while preserving the first occurrence."""

    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = " ".join(str(value).split()).strip(" -–•\t\n")
        key = normalize_text(clean)
        if clean and key not in seen:
            seen.add(key)
            result.append(clean)
    return result


def parse_duration_minutes(value: str | None) -> int | None:
    """Parse ISO-8601 or Vietnamese human-readable durations into minutes."""

    if not value:
        return None

    clean = " ".join(str(value).split()).strip()
    iso_match = _ISO_DURATION_RE.fullmatch(clean)
    if iso_match:
        hours = int(iso_match.group("hours") or 0)
        minutes = int(iso_match.group("minutes") or 0)
        return hours * 60 + minutes

    hours_match = _HOURS_RE.search(clean)
    minutes_match = _MINUTES_RE.search(clean)
    if hours_match or minutes_match:
        hours = int(hours_match.group("hours")) if hours_match else 0
        minutes = int(minutes_match.group("minutes")) if minutes_match else 0
        return hours * 60 + minutes

    if clean.isdigit():
        return int(clean)
    return None

