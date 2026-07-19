import unittest

import scrapy
from scrapy.http import HtmlResponse, Request

from src.crawler.spiders.mon_ngon_moi_ngay import MonNgonMoiNgaySpider


def listing_response(page_number: int, recipe_slugs: list[str]) -> HtmlResponse:
    url = (
        "https://monngonmoingay.com/tim-kiem-mon-ngon/"
        if page_number == 1
        else f"https://monngonmoingay.com/tim-kiem-mon-ngon/page/{page_number}/"
    )
    links = "".join(
        f'<a href="https://monngonmoingay.com/{slug}/">Xem chi tiết</a>'
        for slug in recipe_slugs
    )
    request = Request(url, meta={"page_number": page_number})
    return HtmlResponse(url, body=links.encode(), encoding="utf-8", request=request)


class MonNgonMoiNgaySpiderTests(unittest.TestCase):
    def test_numeric_page_limit_schedules_details_and_next_listing(self) -> None:
        spider = MonNgonMoiNgaySpider(max_pages=2)
        requests = list(spider.parse(listing_response(1, ["pho-bo", "pizza"])))

        self.assertEqual(len(requests), 3)
        detail_requests = [
            request for request in requests if request.callback == spider.parse_recipe
        ]
        listing_requests = [request for request in requests if request.callback == spider.parse]
        self.assertEqual(len(detail_requests), 2)
        self.assertEqual(len(listing_requests), 1)
        self.assertEqual(
            listing_requests[0].url,
            "https://monngonmoingay.com/tim-kiem-mon-ngon/page/2/",
        )

    def test_full_crawl_stops_when_listing_repeats(self) -> None:
        spider = MonNgonMoiNgaySpider(max_pages="all")
        first_requests = list(spider.parse(listing_response(1, ["pho-bo"])))
        repeated_requests = list(spider.parse(listing_response(2, ["pho-bo"])))

        self.assertIsNone(spider.max_pages)
        self.assertTrue(any(request.callback == spider.parse for request in first_requests))
        self.assertEqual(repeated_requests, [])

    def test_full_crawl_has_hard_listing_safety_limit(self) -> None:
        spider = MonNgonMoiNgaySpider(max_pages="all")
        page = spider.FULL_CRAWL_SAFETY_LIMIT
        requests = list(spider.parse(listing_response(page, ["last-recipe"])))

        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0].callback, spider.parse_recipe)

    def test_rejects_invalid_page_limit(self) -> None:
        for value in (0, -1, "unknown"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "positive"):
                MonNgonMoiNgaySpider(max_pages=value)

        self.assertIsInstance(MonNgonMoiNgaySpider(max_pages="ALL"), scrapy.Spider)


if __name__ == "__main__":
    unittest.main()
