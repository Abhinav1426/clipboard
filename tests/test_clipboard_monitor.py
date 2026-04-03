"""Tests for core/clipboard_monitor.py"""

import os
import sys
import tempfile
import time
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import config


def make_monitor(tmp_dir):
    config.CURRENT_FILE = os.path.join(tmp_dir, "current.json")
    config.PINNED_FILE = os.path.join(tmp_dir, "pinned.json")
    config.MAX_PINNED = 50
    config.MAX_ITEMS_IN_MEMORY = 200
    config.MAX_TEXT_LENGTH = 150000
    config.MONITOR_INTERVAL = 0.05  # Fast for tests

    from core.history_manager import HistoryManager
    from core.clipboard_monitor import ClipboardMonitor

    hm = HistoryManager()
    hm.load()
    monitor = ClipboardMonitor(hm)
    return hm, monitor


class TestInternalCopyFlag(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.monitor = make_monitor(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_set_and_clear(self):
        self.assertFalse(self.monitor.is_internal_copy())
        self.monitor.set_internal_copy()
        self.assertTrue(self.monitor.is_internal_copy())
        self.monitor.clear_internal_copy()
        self.assertFalse(self.monitor.is_internal_copy())


class TestCheckClipboard(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.monitor = make_monitor(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def test_new_unique_text_added(self):
        self.monitor._last_content = ""
        with patch("core.clipboard_monitor.pyperclip.paste", return_value="unique text"):
            self.monitor._check_clipboard()
        self.assertEqual(self.hm.count(), 1)
        self.assertEqual(self.hm.get_current_items()[0]["text"], "unique text")

    def test_same_content_not_added_again(self):
        self.monitor._last_content = "same text"
        with patch("core.clipboard_monitor.pyperclip.paste", return_value="same text"):
            self.monitor._check_clipboard()
        self.assertEqual(self.hm.count(), 0)

    def test_whitespace_only_not_added(self):
        self.monitor._last_content = ""
        with patch("core.clipboard_monitor.pyperclip.paste", return_value="   \n\t"):
            self.monitor._check_clipboard()
        self.assertEqual(self.hm.count(), 0)

    def test_internal_copy_flag_prevents_add(self):
        self.monitor._last_content = ""
        self.monitor.set_internal_copy()
        with patch("core.clipboard_monitor.pyperclip.paste", return_value="internal text"):
            self.monitor._check_clipboard()
        self.assertEqual(self.hm.count(), 0)

    def test_duplicate_text_not_added(self):
        self.hm.add("duplicate text")
        self.monitor._last_content = ""
        with patch("core.clipboard_monitor.pyperclip.paste", return_value="duplicate text"):
            self.monitor._check_clipboard()
        # Still only 1 item
        self.assertEqual(self.hm.count(), 1)


class TestMonitorLifecycle(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.hm, self.monitor = make_monitor(self._tmp.name)

    def tearDown(self):
        if self.monitor._running:
            self.monitor.stop()
        self._tmp.cleanup()

    def test_start_creates_daemon_thread(self):
        with patch("core.clipboard_monitor.pyperclip.paste", return_value=""):
            self.monitor.start()
            self.assertIsNotNone(self.monitor._thread)
            self.assertTrue(self.monitor._thread.daemon)
            self.assertTrue(self.monitor._running)

    def test_stop_cleans_up(self):
        with patch("core.clipboard_monitor.pyperclip.paste", return_value=""):
            self.monitor.start()
            self.monitor.stop()
            self.assertFalse(self.monitor._running)

    def test_double_start_safe(self):
        with patch("core.clipboard_monitor.pyperclip.paste", return_value=""):
            self.monitor.start()
            thread1 = self.monitor._thread
            self.monitor.start()  # Should be no-op
            self.assertIs(self.monitor._thread, thread1)

    def test_monitor_captures_new_content(self):
        call_count = [0]
        contents = ["", "captured content"]

        def fake_paste():
            val = contents[min(call_count[0], len(contents) - 1)]
            call_count[0] += 1
            return val

        with patch("core.clipboard_monitor.pyperclip.paste", side_effect=fake_paste):
            self.monitor.start()
            time.sleep(0.3)
            self.monitor.stop()

        self.assertEqual(self.hm.count(), 1)


if __name__ == "__main__":
    unittest.main()
