from unittest import TestCase

from countries import compare_two_countries


class CountriesTests(TestCase):
    def test_compare_two_countries(self):
        result = compare_two_countries("Japan", "Germany")

        self.assertEqual(result["Japan"]["Points"], 2)
        self.assertEqual(result["Germany"]["Points"], 0)