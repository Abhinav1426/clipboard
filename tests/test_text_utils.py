"""Tests for utils/text_utils.py"""

import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.text_utils import truncate, is_empty_or_whitespace, get_preview, content_hash


class TestTruncate(unittest.TestCase):
    def test_under_limit(self):
        text, was = truncate("hello", 10)
        self.assertEqual(text, "hello")
        self.assertFalse(was)

    def test_at_limit(self):
        text, was = truncate("hello", 5)
        self.assertEqual(text, "hello")
        self.assertFalse(was)

    def test_over_limit(self):
        text, was = truncate("hello world", 5)
        self.assertEqual(text, "hello")
        self.assertTrue(was)

    def test_empty_string(self):
        text, was = truncate("", 10)
        self.assertEqual(text, "")
        self.assertFalse(was)


class TestIsEmptyOrWhitespace(unittest.TestCase):
    def test_empty(self):
        self.assertTrue(is_empty_or_whitespace(""))

    def test_spaces(self):
        self.assertTrue(is_empty_or_whitespace("   "))

    def test_tabs_newlines(self):
        self.assertTrue(is_empty_or_whitespace("\t\n\r"))

    def test_real_text(self):
        self.assertFalse(is_empty_or_whitespace("hello"))

    def test_text_with_spaces(self):
        self.assertFalse(is_empty_or_whitespace("  hi  "))


class TestGetPreview(unittest.TestCase):
    def test_short_text_unchanged(self):
        self.assertEqual(get_preview("hello", 100), "hello")

    def test_long_text_truncated(self):
        result = get_preview("a" * 200, 100)
        self.assertTrue(result.endswith("..."))
        self.assertLessEqual(len(result), 103)  # 100 + "..."

    def test_whitespace_collapsed(self):
        result = get_preview("hello   \n\t world", 100)
        self.assertEqual(result, "hello world")

    def test_leading_trailing_stripped(self):
        result = get_preview("  hello  ", 100)
        self.assertEqual(result, "hello")

    def test_exactly_at_limit(self):
        text = "a" * 100
        result = get_preview(text, 100)
        self.assertEqual(result, text)
        self.assertFalse(result.endswith("..."))


class TestContentHash(unittest.TestCase):
    def test_deterministic(self):
        self.assertEqual(content_hash("hello"), content_hash("hello"))

    def test_different_inputs(self):
        self.assertNotEqual(content_hash("hello"), content_hash("world"))

    def test_returns_string(self):
        self.assertIsInstance(content_hash("test"), str)

    def test_hex_format(self):
        h = content_hash("test")
        int(h, 16)  # should not raise


if __name__ == "__main__":
    unittest.main()
