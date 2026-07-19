"""Rate-limited crawler for public Món Ngon Mỗi Ngày recipe pages."""

from __future__ import annotations

from urllib.parse import urlsplit

import scrapy

from src.crawler.extractors.mon_ngon_moi_ngay import NotRecipePage, extract_recipe
from src.preprocessing.normalizer import normalize_text


class MonNgonMoiNgaySpider(scrapy.Spider):
    FULL_CRAWL_SAFETY_LIMIT = 100
    name = "mnmn"
    allowed_domains = ["monngonmoingay.com"]
    start_urls = ["https://monngonmoingay.com/tim-kiem-mon-ngon/"]

    def __init__(self, max_pages: str | int = 5, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self._seen_listing_signatures: set[tuple[str, ...]] = set()
        if str(max_pages).strip().casefold() == "all":
            self.max_pages: int | None = None
            return
        try:
            parsed_max_pages = int(max_pages)
        except (TypeError, ValueError) as exc:
            raise ValueError("max_pages must be a positive integer or 'all'") from exc
        if parsed_max_pages <= 0:
            raise ValueError("max_pages must be a positive integer or 'all'")
        self.max_pages = parsed_max_pages

    def parse(self, response: scrapy.http.Response):
        page_number = int(response.meta.get("page_number", 1))
        detail_urls: set[str] = set()

        for anchor in response.xpath("//a[@href]"):
            label = normalize_text(" ".join(anchor.xpath(".//text()").getall()))
            if "xem chi tiết" not in label:
                continue
            href = anchor.xpath("@href").get()
            if not href:
                continue
            url = response.urljoin(href)
            if urlsplit(url).netloc.endswith("monngonmoingay.com"):
                detail_urls.add(url)

        signature = tuple(sorted(detail_urls))
        if signature and signature in self._seen_listing_signatures:
            self.logger.info(
                "Stopping at listing page %s because its recipe set was already seen",
                page_number,
            )
            return
        if signature:
            self._seen_listing_signatures.add(signature)

        for url in sorted(detail_urls):
            yield response.follow(url, callback=self.parse_recipe)

        within_requested_limit = self.max_pages is None or page_number < self.max_pages
        within_safety_limit = (
            self.max_pages is not None or page_number < self.FULL_CRAWL_SAFETY_LIMIT
        )
        if detail_urls and within_requested_limit and within_safety_limit:
            next_page = page_number + 1
            next_url = f"https://monngonmoingay.com/tim-kiem-mon-ngon/page/{next_page}/"
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={"page_number": next_page},
            )
        elif (
            detail_urls
            and self.max_pages is None
            and page_number >= self.FULL_CRAWL_SAFETY_LIMIT
        ):
            self.logger.warning(
                "Full crawl reached its safety limit of %s listing pages",
                self.FULL_CRAWL_SAFETY_LIMIT,
            )

    def parse_recipe(self, response: scrapy.http.Response):
        try:
            document = extract_recipe(response.body, response.url)
        except NotRecipePage as exc:
            self.logger.warning("Skipping non-recipe page %s: %s", response.url, exc)
            return
        yield document.to_dict()
