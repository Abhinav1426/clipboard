"""Tests for core/archive_manager.py"""

import os
import re
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def make_history_and_archive(tmp_dir, items_per_file=150):
    config.CURRENT_FILE = os.path.join(tmp_dir, "current.json")
    config.PINNED_FILE = os.path.join(tmp_dir, "pinned.json")
    config.ARCHIVE_DIR = os.path.join(tmp_dir, "archive")
    config.ITEMS_PER_FILE = items_per_file
    config.MAX_PINNED = 50
    config.MAX_ITEMS_IN_MEMORY = 500
    config.MAX_TEXT_LENGTH = 150000

    from core.history_manager import HistoryManager
    from core.archive_manager import ArchiveManager

    hm = HistoryManager()
    hm.load()
    am = ArchiveManager(hm)
    return hm, am


class TestCreateArchiveFilename(unittest.TestCase):
    def test_format(self):
        from core.archive_manager import ArchiveManager
        name = ArchiveManager.create_archive_filename()
        self.assertRegex(name, r"^history_\d{8}_\d{6}\.json$")


class TestCheckAndRotate(unittest.TestCase):
    def setUp(self):
        # Use 55 as threshold: add 55 items → keep 50, archive 5
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am = make_history_and_archive(self._tmp.name, items_per_file=55)

    def tearDown(self):
        self._tmp.cleanup()

    def test_no_rotation_below_threshold(self):
        for i in range(54):
            self.hm.add(f"item{i}")
        result = self.am.check_and_rotate()
        self.assertFalse(result)

    def test_rotation_at_threshold(self):
        for i in range(55):
            self.hm.add(f"item{i}")
        result = self.am.check_and_rotate()
        self.assertTrue(result)
        archives = self.am.get_archive_files()
        self.assertEqual(len(archives), 1)


class TestRotateHistory(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am = make_history_and_archive(self._tmp.name, items_per_file=10)

    def tearDown(self):
        self._tmp.cleanup()

    def test_keeps_50_in_current(self):
        # Add 60 items with threshold=10 so rotate is triggered
        # But we want to test the keep-50 logic, so we manually load enough
        config.ITEMS_PER_FILE = 60
        for i in range(60):
            self.hm.add(f"item{i}")
        rotated = self.am.rotate_history()
        self.assertTrue(rotated)
        self.assertEqual(self.hm.count(), 50)

    def test_archives_the_rest(self):
        config.ITEMS_PER_FILE = 60
        for i in range(60):
            self.hm.add(f"item{i}")
        self.am.rotate_history()
        stats = self.am.get_archive_stats()
        self.assertEqual(stats["total_items"], 10)

    def test_pinned_not_archived(self):
        config.ITEMS_PER_FILE = 60
        for i in range(60):
            self.hm.add(f"item{i}")
        # Pin one
        pinned_id = self.hm.get_current_items()[0]["id"]
        self.hm.toggle_pin(pinned_id)
        self.am.rotate_history()
        self.assertEqual(self.hm.pinned_count(), 1)


class TestGetArchiveFiles(unittest.TestCase):
    def setUp(self):
        # Use 55 so that with 55 items, 5 are archived (keep 50)
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am = make_history_and_archive(self._tmp.name, items_per_file=55)

    def tearDown(self):
        self._tmp.cleanup()

    def test_sorted_newest_first(self):
        import time
        config.ITEMS_PER_FILE = 55
        for i in range(55):
            self.hm.add(f"batch1-{i}")
        self.am.rotate_history()
        time.sleep(1.1)  # Ensure different filename timestamp
        for i in range(55):
            self.hm.add(f"batch2-{i}")
        self.am.rotate_history()
        files = self.am.get_archive_files()
        self.assertEqual(len(files), 2)
        # Newest file comes first (sorted descending by name = timestamp)
        self.assertGreater(files[0], files[1])


class TestGetArchiveStats(unittest.TestCase):
    def setUp(self):
        # Use 55 so that with 55 items, 5 are archived (keep 50)
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.am = make_history_and_archive(self._tmp.name, items_per_file=55)

    def tearDown(self):
        self._tmp.cleanup()

    def test_empty_stats(self):
        stats = self.am.get_archive_stats()
        self.assertEqual(stats["file_count"], 0)
        self.assertEqual(stats["total_items"], 0)

    def test_stats_after_rotation(self):
        config.ITEMS_PER_FILE = 55
        for i in range(55):
            self.hm.add(f"item{i}")
        self.am.rotate_history()
        stats = self.am.get_archive_stats()
        self.assertEqual(stats["file_count"], 1)
        self.assertEqual(stats["total_items"], 5)  # 55 added - 50 kept = 5 archived


if __name__ == "__main__":
    unittest.main()
