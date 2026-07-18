import unittest

from src.query import SearchFilters


class SearchFiltersTests(unittest.TestCase):
    def setUp(self) -> None:
        self.document = {
            "total_time_minutes": 20,
            "difficulty": "Dễ",
            "categories": ["Món chay", "Bữa tối"],
            "ingredients": ["Đậu hũ non", "Nấm đông cô"],
            "cooking_method": "nướng",
        }

    def test_matches_accentless_structured_constraints(self) -> None:
        filters = SearchFilters(
            max_time_minutes=30,
            difficulty="de",
            categories=("mon chay",),
            ingredients=("dau hu",),
            cooking_methods=("nuong",),
        )

        self.assertTrue(filters.active)
        self.assertTrue(filters.matches(self.document))

    def test_rejects_document_outside_time_or_category(self) -> None:
        self.assertFalse(SearchFilters(max_time_minutes=10).matches(self.document))
        self.assertFalse(SearchFilters(categories=("món mặn",)).matches(self.document))

    def test_filters_document_ids_and_serializes_tuples_as_lists(self) -> None:
        documents = {
            "match": self.document,
            "slow": {**self.document, "total_time_minutes": 60},
        }
        filters = SearchFilters(max_time_minutes=30, categories=("món chay",))

        self.assertEqual(filters.filter_document_ids(documents), {"match"})
        self.assertEqual(filters.to_dict()["categories"], ["món chay"])

    def test_rejects_negative_time(self) -> None:
        with self.assertRaisesRegex(ValueError, "negative"):
            SearchFilters(max_time_minutes=-1)


if __name__ == "__main__":
    unittest.main()
