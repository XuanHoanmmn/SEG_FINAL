"""Rate-limited crawler for public Món Ngon Mỗi Ngày recipe pages."""

from __future__ import annotations

from urllib.parse import urlsplit

import scrapy

from src.crawler.extractors.mon_ngon_moi_ngay import NotRecipePage, extract_recipe
from src.preprocessing.normalizer import normalize_text


class MonNgonMoiNgaySpider(scrapy.Spider):
    name = "mnmn"
    allowed_domains = ["monngonmoingay.com"]
    start_urls = ["https://monngonmoingay.com/tim-kiem-mon-ngon/"]

    def __init__(self, max_pages: str | int = 5, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        try:
            self.max_pages = max(1, int(max_pages))
        except (TypeError, ValueError) as exc:
            raise ValueError("max_pages must be a positive integer") from exc

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

        for url in sorted(detail_urls):
            yield response.follow(url, callback=self.parse_recipe)

        if detail_urls and page_number < self.max_pages:
            next_page = page_number + 1
            next_url = f"https://monngonmoingay.com/tim-kiem-mon-ngon/page/{next_page}/"
            yield scrapy.Request(
                next_url,
                callback=self.parse,
                meta={"page_number": next_page},
            )

    def parse_recipe(self, response: scrapy.http.Response):
        try:
            document = extract_recipe(response.body, response.url)
        except NotRecipePage as exc:
            self.logger.warning("Skipping non-recipe page %s: %s", response.url, exc)
            return
        yield document.to_dict()

