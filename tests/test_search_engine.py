"""Tests for core/search_engine.py"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def make_engine(tmp_dir):
    config.CURRENT_FILE = os.path.join(tmp_dir, "current.json")
    config.PINNED_FILE = os.path.join(tmp_dir, "pinned.json")
    config.ARCHIVE_DIR = os.path.join(tmp_dir, "archive")
    config.ITEMS_PER_FILE = 150
    config.MAX_PINNED = 50
    config.MAX_ITEMS_IN_MEMORY = 200
    config.MAX_TEXT_LENGTH = 150000
    config.SEARCH_CACHE_TTL = 300
    config.PREVIEW_MAX_CHARS = 100

    from core.history_manager import HistoryManager
    from core.archive_manager import ArchiveManager
    from core.search_engine import SearchEngine

    hm = HistoryManager()
    hm.load()
    am = ArchiveManager(hm)
    se = SearchEngine(hm, am)
    return hm, am, se


class TestSearchCurrent(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am, self.se = make_engine(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_finds_match(self):
        self.hm.add("Hello World")
        self.hm.add("Foo Bar")
        results = self.se.search_current("hello")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["text"], "Hello World")

    def test_case_insensitive(self):
        self.hm.add("UPPERCASE TEXT")
        results = self.se.search_current("uppercase")
        self.assertEqual(len(results), 1)

    def test_returns_source_file_memory(self):
        self.hm.add("test content")
        results = self.se.search_current("test")
        self.assertEqual(results[0]["source_file"], "memory")

    def test_returns_match_preview(self):
        self.hm.add("test content here")
        results = self.se.search_current("test")
        self.assertIn("match_preview", results[0])

    def test_no_match_returns_empty(self):
        self.hm.add("Hello World")
        results = self.se.search_current("xyz")
        self.assertEqual(results, [])

    def test_empty_query_matches_all(self):
        # search_current("") — empty string is substring of everything, returns all items
        self.hm.add("Hello World")
        results = self.se.search_current("")
        self.assertEqual(len(results), 1)

    def test_searches_pinned_too(self):
        entry = self.hm.add("pinned item")
        self.hm.toggle_pin(entry["id"])
        results = self.se.search_current("pinned")
        self.assertEqual(len(results), 1)


class TestGetSearchResults(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am, self.se = make_engine(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_archives_by_default(self):
        self.hm.add("result")
        results = self.se.get_search_results("result", include_archives=False)
        self.assertTrue(all(r["source_file"] == "memory" for r in results))

    def test_empty_query_returns_empty(self):
        self.hm.add("something")
        results = self.se.get_search_results("   ")
        self.assertEqual(results, [])


class TestSearchArchiveCache(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am, self.se = make_engine(self._tmp.name)
        os.makedirs(config.ARCHIVE_DIR, exist_ok=True)

    def tearDown(self):
        self._tmp.cleanup()

    def _make_archive_file(self, filename, entries):
        from utils.file_utils import save_json
        path = os.path.join(config.ARCHIVE_DIR, filename)
        save_json(path, entries)

    def test_archive_search_finds_match(self):
        self._make_archive_file(
            "history_20240101_120000.json",
            [{"id": "x", "text": "archived content", "timestamp": "2024", "pinned": False, "source": "external"}]
        )
        results = self.se.search_archive("archived", "history_20240101_120000.json")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["source_file"], "history_20240101_120000.json")

    def test_cache_is_used_on_second_call(self):
        self._make_archive_file(
            "history_20240101_120000.json",
            [{"id": "x", "text": "cached content", "timestamp": "2024", "pinned": False, "source": "external"}]
        )
        # First call populates cache
        r1 = self.se.search_archive("cached", "history_20240101_120000.json")
        # Overwrite file to verify cache is served, not file
        self._make_archive_file("history_20240101_120000.json", [])
        r2 = self.se.search_archive("cached", "history_20240101_120000.json")
        self.assertEqual(len(r1), len(r2))

    def test_cache_expires_after_ttl(self):
        config.SEARCH_CACHE_TTL = 1
        self._make_archive_file(
            "history_20240101_120000.json",
            [{"id": "x", "text": "expiring content", "timestamp": "2024", "pinned": False, "source": "external"}]
        )
        self.se.search_archive("expiring", "history_20240101_120000.json")
        # Overwrite file
        self._make_archive_file("history_20240101_120000.json", [])
        # Advance time past TTL
        with patch("core.search_engine.time.time", return_value=time.time() + 2):
            r2 = self.se.search_archive("expiring", "history_20240101_120000.json")
        self.assertEqual(r2, [])

    def test_clear_cache(self):
        self._make_archive_file(
            "history_20240101_120000.json",
            [{"id": "x", "text": "data", "timestamp": "2024", "pinned": False, "source": "external"}]
        )
        self.se.search_archive("data", "history_20240101_120000.json")
        self.assertGreater(len(self.se._cache), 0)
        self.se.clear_cache()
        self.assertEqual(len(self.se._cache), 0)


if __name__ == "__main__":
    unittest.main()
