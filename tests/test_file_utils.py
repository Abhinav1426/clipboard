"""Tests for utils/file_utils.py"""

import json
import os
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.file_utils import ensure_dir, load_json, save_json


class TestEnsureDir(unittest.TestCase):
    def test_creates_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "newdir")
            self.assertFalse(os.path.exists(target))
            ensure_dir(target)
            self.assertTrue(os.path.isdir(target))

    def test_idempotent_on_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            ensure_dir(tmp)  # already exists — should not raise
            self.assertTrue(os.path.isdir(tmp))

    def test_creates_nested(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = os.path.join(tmp, "a", "b", "c")
            ensure_dir(target)
            self.assertTrue(os.path.isdir(target))


class TestLoadJson(unittest.TestCase):
    def test_missing_file_returns_empty(self):
        result = load_json("/nonexistent/path/file.json")
        self.assertEqual(result, [])

    def test_valid_json_list(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump([{"id": "1"}, {"id": "2"}], f)
            path = f.name
        try:
            result = load_json(path)
            self.assertEqual(len(result), 2)
            self.assertEqual(result[0]["id"], "1")
        finally:
            os.unlink(path)

    def test_corrupt_json_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ not valid json !!!")
            path = f.name
        try:
            result = load_json(path)
            self.assertEqual(result, [])
            # Backup should exist
            self.assertTrue(os.path.exists(path + ".corrupt"))
        finally:
            os.unlink(path)
            corrupt = path + ".corrupt"
            if os.path.exists(corrupt):
                os.unlink(corrupt)

    def test_non_list_json_returns_empty(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"key": "value"}, f)
            path = f.name
        try:
            result = load_json(path)
            self.assertEqual(result, [])
        finally:
            os.unlink(path)


class TestSaveJson(unittest.TestCase):
    def test_saves_and_roundtrips(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            data = [{"id": "abc", "text": "hello"}]
            ok = save_json(path, data)
            self.assertTrue(ok)
            loaded = load_json(path)
            self.assertEqual(loaded, data)

    def test_overwrites_existing(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            save_json(path, [{"v": 1}])
            save_json(path, [{"v": 2}])
            result = load_json(path)
            self.assertEqual(result[0]["v"], 2)

    def test_atomic_no_leftover_tmp(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "data.json")
            save_json(path, [])
            tmp_files = [f for f in os.listdir(tmp) if f.endswith(".tmp")]
            self.assertEqual(tmp_files, [])


if __name__ == "__main__":
    unittest.main()
