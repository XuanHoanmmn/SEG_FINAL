"""Extract Món Ngon Mỗi Ngày pages without depending on fragile CSS classes."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from lxml import etree, html

from src.crawler.utils import (
    canonicalize_url,
    deduplicate_texts,
    make_content_hash,
    make_document_id,
    parse_duration_minutes,
)
from src.models import RecipeDocument
from src.preprocessing.normalizer import normalize_text, strip_accents

_SECTION_LABELS = {
    "mo ta": "description",
    "nguyen lieu": "ingredients",
    "so che": "preparation",
    "thuc hien": "instructions",
    "cach dung": "serving",
    "mach nho": "tips",
}
_METHODS = (
    "quay",
    "rôti",
    "nướng",
    "chiên",
    "hấp",
    "tiềm",
    "gỏi",
    "trộn",
    "hầm",
    "lẩu",
    "xào",
    "canh",
    "súp",
    "om",
    "rim",
    "kho",
)


class NotRecipePage(ValueError):
    """Raised when a public page does not contain enough recipe information."""


def _clean_text(value: object) -> str:
    return " ".join(str(value or "").split()).strip()


def _normalized_label(value: str) -> str:
    return strip_accents(normalize_text(value)).strip(" :.-")


def _classify_section(value: str) -> str | None:
    label = _normalized_label(value)
    for prefix, section in _SECTION_LABELS.items():
        if label == prefix or label.startswith(f"{prefix} "):
            return section
    return None


def _meta_content(root: html.HtmlElement, *keys: str) -> str:
    for key in keys:
        values = root.xpath(
            "//meta[@name=$key or @property=$key]/@content",
            key=key,
        )
        if values and _clean_text(values[0]):
            return _clean_text(values[0])
    return ""


def _find_recipe_jsonld(root: html.HtmlElement) -> dict[str, Any] | None:
    def walk(value: Any) -> dict[str, Any] | None:
        if isinstance(value, list):
            for item in value:
                found = walk(item)
                if found:
                    return found
        elif isinstance(value, dict):
            item_type = value.get("@type")
            types = item_type if isinstance(item_type, list) else [item_type]
            if any(str(candidate).lower() == "recipe" for candidate in types):
                return value
            for child in value.values():
                found = walk(child)
                if found:
                    return found
        return None

    for script_text in root.xpath("//script[@type='application/ld+json']/text()"):
        try:
            found = walk(json.loads(script_text))
        except (TypeError, json.JSONDecodeError):
            continue
        if found:
            return found
    return None


def _instruction_texts(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        text = value.get("text") or value.get("name")
        return [str(text)] if text else []
    if isinstance(value, list):
        result: list[str] = []
        for item in value:
            result.extend(_instruction_texts(item))
        return result
    return []


def _image_url(value: Any) -> str | None:
    if isinstance(value, str):
        return value
    if isinstance(value, list) and value:
        return _image_url(value[0])
    if isinstance(value, dict):
        candidate = value.get("url") or value.get("contentUrl")
        return str(candidate) if candidate else None
    return None


def _from_jsonld(data: dict[str, Any], url: str) -> RecipeDocument:
    title = _clean_text(data.get("name"))
    ingredients = deduplicate_texts(data.get("recipeIngredient") or [])
    instructions = deduplicate_texts(_instruction_texts(data.get("recipeInstructions")))
    if not title or not ingredients or not instructions:
        raise NotRecipePage("JSON-LD Recipe is missing title, ingredients or instructions")

    categories_value = data.get("recipeCategory") or []
    categories = [categories_value] if isinstance(categories_value, str) else categories_value
    canonical_url = canonicalize_url(url)
    document = RecipeDocument(
        doc_id=make_document_id(canonical_url),
        title=title,
        url=canonical_url,
        source="monngonmoingay.com",
        description=_clean_text(data.get("description")),
        ingredients=ingredients,
        instructions=instructions,
        categories=deduplicate_texts(categories),
        prep_time_minutes=parse_duration_minutes(data.get("prepTime")),
        cook_time_minutes=parse_duration_minutes(data.get("cookTime") or data.get("totalTime")),
        servings=_clean_text(data.get("recipeYield")) or None,
        image_url=_image_url(data.get("image")),
        crawled_at=datetime.now(UTC).isoformat(),
    )
    document.content_hash = make_content_hash(
        document.title,
        document.ingredients,
        document.instructions,
    )
    return document


def _extract_sections(root: html.HtmlElement) -> dict[str, list[str]]:
    elements = list(root.iter())
    sections: dict[str, list[str]] = {name: [] for name in _SECTION_LABELS.values()}

    for index, element in enumerate(elements):
        if not isinstance(element.tag, str) or element.tag.lower() not in {
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "strong",
            "b",
        }:
            continue
        section = _classify_section(_clean_text(element.text_content()))
        if not section:
            continue

        collected: list[str] = []
        for candidate in elements[index + 1 :]:
            if not isinstance(candidate.tag, str):
                continue
            tag = candidate.tag.lower()
            candidate_text = _clean_text(candidate.text_content())
            if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
                break
            if tag in {"strong", "b"} and _classify_section(candidate_text):
                break
            if tag not in {"li", "p"} or not candidate_text:
                continue
            parent = candidate.getparent()
            if (
                parent is not None
                and isinstance(parent.tag, str)
                and parent.tag.lower() in {"li", "p"}
            ):
                continue
            collected.append(candidate_text)
        sections[section].extend(collected)

    return {name: deduplicate_texts(values) for name, values in sections.items()}


def _find_labeled_value(root: html.HtmlElement, *labels: str) -> str | None:
    normalized_labels = [_normalized_label(label) for label in labels]
    for element in root.iter():
        if not isinstance(element.tag, str):
            continue
        text = _clean_text(element.text_content())
        if not text or len(text) > 160:
            continue
        normalized = _normalized_label(text)
        for label in normalized_labels:
            if normalized == label:
                continue
            if normalized.startswith(label):
                raw_parts = text.split(":", maxsplit=1)
                if len(raw_parts) == 2 and _clean_text(raw_parts[1]):
                    return _clean_text(raw_parts[1])
                return _clean_text(text[len(labels[normalized_labels.index(label)]) :]).lstrip(": ")
    return None


def _extract_categories(root: html.HtmlElement) -> list[str]:
    values = root.xpath(
        "//a[@rel='tag' or contains(concat(' ', normalize-space(@class), ' '), ' tag ')]//text()"
    )
    return deduplicate_texts(_clean_text(value) for value in values)


def _infer_cooking_method(title: str, categories: list[str]) -> str | None:
    haystack = normalize_text(" ".join([title, *categories]))
    for method in _METHODS:
        if normalize_text(method) in haystack:
            return method
    return None


def _from_dom(root: html.HtmlElement, url: str) -> RecipeDocument:
    title_values = root.xpath("//h1[1]//text()")
    title = _clean_text(" ".join(title_values)) or _meta_content(root, "og:title")
    sections = _extract_sections(root)
    ingredients = sections["ingredients"]
    instructions = deduplicate_texts(
        [
            *sections["preparation"],
            *sections["instructions"],
            *sections["serving"],
        ]
    )
    if not title or not ingredients or not instructions:
        raise NotRecipePage("Page is missing title, ingredients or instructions")

    categories = _extract_categories(root)
    canonical_url = canonicalize_url(url)
    duration = _find_labeled_value(root, "Thời gian thực hiện", "Thời gian")
    description = _meta_content(root, "description", "og:description")
    if not description and sections["description"]:
        description = " ".join(sections["description"])

    document = RecipeDocument(
        doc_id=make_document_id(canonical_url),
        title=title,
        url=canonical_url,
        source="monngonmoingay.com",
        description=description,
        ingredients=ingredients,
        instructions=instructions,
        categories=categories,
        cooking_method=_infer_cooking_method(title, categories),
        cook_time_minutes=parse_duration_minutes(duration),
        servings=_find_labeled_value(root, "Khẩu phần"),
        difficulty=_find_labeled_value(root, "Độ khó"),
        image_url=_meta_content(root, "og:image") or None,
        crawled_at=datetime.now(UTC).isoformat(),
    )
    document.content_hash = make_content_hash(
        document.title,
        document.ingredients,
        document.instructions,
    )
    return document


def extract_recipe(html_text: str | bytes, url: str) -> RecipeDocument:
    """Extract one recipe using JSON-LD first and semantic DOM headings second."""

    try:
        root = html.fromstring(html_text)
    except (etree.ParserError, TypeError, ValueError) as exc:
        raise NotRecipePage("Invalid HTML document") from exc

    jsonld = _find_recipe_jsonld(root)
    if jsonld:
        return _from_jsonld(jsonld, url)
    return _from_dom(root, url)
