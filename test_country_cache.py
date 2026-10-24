import json
import os
from contextlib import chdir
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import Mock, patch

import countries


class CountryCacheTests(TestCase):
    now = 1_800_000_000

    def setUp(self):
        directory = self.enterContext(TemporaryDirectory())
        self.enterContext(chdir(directory))
        self.enterContext(patch("countries.time.time", return_value=self.now))
        self.api = self.enterContext(patch("countries.requests.get"))
        self.api.side_effect = AssertionError("A fresh cache must not use the API")
        self.records = [
            {"names": {"common": "Japan"}, "population": 125_000_000,
             "area": {"kilometers": 377_975}, "flag": {"emoji": "JP"}},
            {"names": {"common": "Germany"}, "population": 83_000_000,
             "area": {"kilometers": 357_022}, "flag": {"emoji": "DE"}},
        ]
        countries._read_country_cache.cache_clear()
        self.addCleanup(countries._read_country_cache.cache_clear)
        self.write_cache()

    def write_cache(self, timestamp=None, path="countries.json"):
        Path(path).write_text(json.dumps({
            "timestamp": self.now if timestamp is None else timestamp,
            "countries": self.records,
        }), encoding="utf-8")

    def prepare_api(self):
        self.api.side_effect = [
            Mock(json=Mock(return_value={"data": {"objects": self.records}})),
            Mock(json=Mock(return_value={"data": {"objects": []}})),
            Mock(json=Mock(return_value={"data": {"objects": []}})),
        ]

    def test_rounds_reuse_one_parse_without_exposing_mutable_records(self):
        with patch("countries.json.load", wraps=json.load) as loads:
            first = countries.get_one_country("JAPAN")
            first["Population"] = 0
            for _ in range(5):
                comparison = countries.compare_two_countries("Japan", "Germany")
                self.assertEqual(comparison["Japan"]["Points"], 2)
                self.assertEqual(comparison["Japan"]["Population"], 125_000_000)
                self.assertEqual(len(countries.select_and_compare_random_countries()), 2)
            self.assertEqual(loads.call_count, 1)
        self.api.assert_not_called()

    def test_worker_sees_atomic_replacement_even_with_preserved_timestamp(self):
        self.assertEqual(countries.get_one_country("Japan")["Population"], 125_000_000)
        original_stat = Path("countries.json").stat()
        self.records[0]["population"] = 126_000_000
        self.write_cache(path="replacement.json")
        os.utime("replacement.json", ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
        os.replace("replacement.json", "countries.json")
        self.assertEqual(countries.get_one_country("Japan")["Population"], 126_000_000)

    def test_expired_cache_refreshes_once_then_reuses_the_new_snapshot(self):
        self.write_cache(timestamp=self.now - 604801)
        self.assertTrue(countries.is_country_cache_expired())
        self.records[0]["population"] = 126_000_000
        self.prepare_api()
        for _ in range(3):
            self.assertEqual(countries.get_one_country("Japan")["Population"], 126_000_000)
        self.assertEqual(self.api.call_count, 3)
        self.assertFalse(countries.is_country_cache_expired())

    def test_missing_cache_downloads_a_complete_snapshot(self):
        Path("countries.json").unlink()
        self.prepare_api()
        self.assertEqual(countries.get_one_country("Germany")["Name"], "Germany")
        self.assertEqual(self.api.call_count, 3)
        self.assertTrue(Path("countries.json").exists())

    def test_failed_write_keeps_the_last_complete_snapshot(self):
        original = Path("countries.json").read_bytes()
        self.prepare_api()
        with patch("countries.json.dump", side_effect=OSError("Disk full")):
            with self.assertRaisesRegex(OSError, "Disk full"):
                countries.refresh_country_cache()
        self.assertEqual(Path("countries.json").read_bytes(), original)
        self.assertEqual(list(Path.cwd().glob(".countries-*.json")), [])
        self.assertEqual(countries.get_one_country("Japan")["Population"], 125_000_000)

    def test_unknown_country_remains_an_error(self):
        with self.assertRaisesRegex(ValueError, "This country was not found"):
            countries.get_one_country("Atlantis")
