"""Tests for core/history_manager.py"""

import os
import sys
import tempfile
import threading
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def make_manager(tmp_dir):
    """Create a HistoryManager wired to a temp directory."""
    config.CURRENT_FILE = os.path.join(tmp_dir, "current.json")
    config.PINNED_FILE = os.path.join(tmp_dir, "pinned.json")
    from core.history_manager import HistoryManager
    hm = HistoryManager()
    hm.load()
    return hm


class TestHistoryManagerAdd(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_add_returns_entry_with_schema(self):
        entry = self.hm.add("hello world")
        self.assertIsNotNone(entry)
        self.assertIn("id", entry)
        self.assertIn("text", entry)
        self.assertIn("timestamp", entry)
        self.assertFalse(entry["pinned"])
        self.assertEqual(entry["text"], "hello world")

    def test_add_inserts_at_front(self):
        self.hm.add("first")
        self.hm.add("second")
        items = self.hm.get_current_items()
        self.assertEqual(items[0]["text"], "second")

    def test_add_whitespace_returns_none(self):
        result = self.hm.add("   \t\n")
        self.assertIsNone(result)
        self.assertEqual(self.hm.count(), 0)

    def test_add_empty_string_returns_none(self):
        result = self.hm.add("")
        self.assertIsNone(result)

    def test_add_truncates_long_text(self):
        config.MAX_TEXT_LENGTH = 10
        entry = self.hm.add("hello world this is long")
        self.assertTrue(entry.get("truncated"))
        self.assertEqual(len(entry["text"]), 10)

    def test_add_no_truncation_flag_for_short(self):
        entry = self.hm.add("short")
        self.assertNotIn("truncated", entry)


class TestHistoryManagerDuplicate(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_duplicate_in_pinned(self):
        self.hm.add("test")
        self.hm.toggle_pin(self.hm.get_current_items()[0]["id"])
        self.assertTrue(self.hm.is_duplicate("test"))

    def test_duplicate_in_last_5_current(self):
        self.hm.add("alpha")
        self.assertTrue(self.hm.is_duplicate("alpha"))

    def test_not_duplicate_beyond_last_5(self):
        self.hm.add("old")
        for i in range(5):
            self.hm.add(f"item{i}")
        # "old" is now at position 5+ (0-indexed), beyond the last-5 window
        self.assertFalse(self.hm.is_duplicate("old"))

    def test_unique_text_not_duplicate(self):
        self.hm.add("something")
        self.assertFalse(self.hm.is_duplicate("different"))


class TestHistoryManagerDelete(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_delete_from_current(self):
        entry = self.hm.add("hello")
        ok = self.hm.delete(entry["id"])
        self.assertTrue(ok)
        self.assertEqual(self.hm.count(), 0)

    def test_delete_from_pinned(self):
        entry = self.hm.add("hello")
        self.hm.toggle_pin(entry["id"])
        ok = self.hm.delete(entry["id"])
        self.assertTrue(ok)
        self.assertEqual(self.hm.pinned_count(), 0)

    def test_delete_unknown_returns_false(self):
        ok = self.hm.delete("nonexistent-uuid")
        self.assertFalse(ok)


class TestHistoryManagerTogglePin(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 3
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_pin_moves_to_pinned(self):
        entry = self.hm.add("hello")
        self.hm.toggle_pin(entry["id"])
        self.assertEqual(self.hm.pinned_count(), 1)
        self.assertEqual(self.hm.count(), 0)

    def test_unpin_moves_to_current(self):
        entry = self.hm.add("hello")
        self.hm.toggle_pin(entry["id"])
        self.hm.toggle_pin(entry["id"])
        self.assertEqual(self.hm.pinned_count(), 0)
        self.assertEqual(self.hm.count(), 1)

    def test_enforces_max_pinned(self):
        ids = []
        for i in range(4):
            e = self.hm.add(f"item{i}")
            ids.append(e["id"])
        # Pin first 3 — should succeed
        for i in range(3):
            ok = self.hm.toggle_pin(ids[i])
            self.assertTrue(ok)
        # Pin 4th — should fail (MAX_PINNED=3)
        ok = self.hm.toggle_pin(ids[3])
        self.assertFalse(ok)
        self.assertEqual(self.hm.pinned_count(), 3)


class TestHistoryManagerClearAll(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_clear_removes_current(self):
        self.hm.add("a")
        self.hm.add("b")
        self.hm.clear_all()
        self.assertEqual(self.hm.count(), 0)

    def test_clear_preserves_pinned(self):
        entry = self.hm.add("pinned")
        self.hm.toggle_pin(entry["id"])
        self.hm.add("unpinned")
        self.hm.clear_all()
        self.assertEqual(self.hm.pinned_count(), 1)
        self.assertEqual(self.hm.count(), 0)


class TestHistoryManagerCounts(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 200
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_count_and_total(self):
        e1 = self.hm.add("a")
        e2 = self.hm.add("b")
        self.hm.toggle_pin(e1["id"])
        self.assertEqual(self.hm.count(), 1)
        self.assertEqual(self.hm.pinned_count(), 1)
        self.assertEqual(self.hm.total_count(), 2)

    def test_get_by_id_found(self):
        entry = self.hm.add("hello")
        result = self.hm.get_by_id(entry["id"])
        self.assertIsNotNone(result)
        self.assertEqual(result["text"], "hello")

    def test_get_by_id_not_found(self):
        result = self.hm.get_by_id("fake-uuid")
        self.assertIsNone(result)


class TestHistoryManagerThreadSafety(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        config.MAX_PINNED = 50
        config.MAX_ITEMS_IN_MEMORY = 500
        config.MAX_TEXT_LENGTH = 150000
        self.hm = make_manager(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_concurrent_add(self):
        errors = []

        def add_items(prefix):
            try:
                for i in range(20):
                    self.hm.add(f"{prefix}-item-{i}")
            except Exception as e:
                errors.append(e)

        t1 = threading.Thread(target=add_items, args=("A",))
        t2 = threading.Thread(target=add_items, args=("B",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        self.assertEqual(errors, [])
        self.assertEqual(self.hm.count(), 40)


if __name__ == "__main__":
    unittest.main()
