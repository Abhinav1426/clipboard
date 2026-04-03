"""Tests for UI selection behavior — verifies that single-click selection
does NOT rebuild the list (which would prevent double-click from firing)."""

import os
import sys
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class FakeWidget:
    """Minimal stand-in for a tkinter/CTk widget."""

    def __init__(self):
        self._config = {}

    def configure(self, **kwargs):
        self._config.update(kwargs)

    config = configure  # tk.Widget alias

    def winfo_children(self):
        return []


class TestModernUISelectItem(unittest.TestCase):
    """Ensure ModernUI._select_item updates visuals without calling refresh_list."""

    def _make_ui(self):
        from ui.modern_ui import ModernUI

        ui = ModernUI.__new__(ModernUI)
        ui.history = MagicMock()
        ui.archive = MagicMock()
        ui.search = MagicMock()
        ui.auto_paste = MagicMock()
        ui._selected_id = None
        ui._item_widgets = []
        ui._item_map = {}
        ui._detail_text = MagicMock()
        ui._detail_info = MagicMock()
        return ui

    def test_select_item_sets_selected_id(self):
        ui = self._make_ui()
        row_a, label_a = FakeWidget(), FakeWidget()
        row_b, label_b = FakeWidget(), FakeWidget()
        ui._item_map = {
            "id-a": {"row": row_a, "label": label_a},
            "id-b": {"row": row_b, "label": label_b},
        }

        ui._select_item("id-a")

        self.assertEqual(ui.get_selected_id(), "id-a")

    def test_select_item_highlights_selected_row(self):
        ui = self._make_ui()
        row_a, label_a = FakeWidget(), FakeWidget()
        row_b, label_b = FakeWidget(), FakeWidget()
        ui._item_map = {
            "id-a": {"row": row_a, "label": label_a},
            "id-b": {"row": row_b, "label": label_b},
        }

        ui._select_item("id-a")

        self.assertEqual(row_a._config["fg_color"], "#3c3c54")
        self.assertEqual(label_a._config["text_color"], "#ddd")
        self.assertEqual(row_b._config["fg_color"], "#1e1e2e")
        self.assertEqual(label_b._config["text_color"], "#bbb")

    def test_select_item_does_not_call_refresh_list(self):
        ui = self._make_ui()
        ui.refresh_list = MagicMock()
        row, label = FakeWidget(), FakeWidget()
        ui._item_map = {"id-x": {"row": row, "label": label}}

        ui._select_item("id-x")

        ui.refresh_list.assert_not_called()

    def test_switching_selection_unhighlights_previous(self):
        ui = self._make_ui()
        row_a, label_a = FakeWidget(), FakeWidget()
        row_b, label_b = FakeWidget(), FakeWidget()
        ui._item_map = {
            "id-a": {"row": row_a, "label": label_a},
            "id-b": {"row": row_b, "label": label_b},
        }

        ui._select_item("id-a")
        ui._select_item("id-b")

        self.assertEqual(row_a._config["fg_color"], "#1e1e2e")
        self.assertEqual(row_b._config["fg_color"], "#3c3c54")


class TestClassicUISelectItem(unittest.TestCase):
    """Ensure ClassicUI._select_item updates visuals without calling refresh_list."""

    def _make_ui(self):
        from ui.classic_ui import ClassicUI

        ui = ClassicUI.__new__(ClassicUI)
        ui.history = MagicMock()
        ui.archive = MagicMock()
        ui.search = MagicMock()
        ui.auto_paste = MagicMock()
        ui._selected_id = None
        ui._item_widgets = []
        ui._item_map = {}
        ui._detail_text = MagicMock()
        ui._detail_info = MagicMock()
        return ui

    def test_select_item_sets_selected_id(self):
        ui = self._make_ui()
        row, label = FakeWidget(), FakeWidget()
        row.winfo_children = lambda: [label]
        ui._item_map = {"id-a": {"row": row, "label": label}}

        ui._select_item("id-a")

        self.assertEqual(ui.get_selected_id(), "id-a")

    def test_select_item_does_not_call_refresh_list(self):
        ui = self._make_ui()
        ui.refresh_list = MagicMock()
        row, label = FakeWidget(), FakeWidget()
        row.winfo_children = lambda: [label]
        ui._item_map = {"id-x": {"row": row, "label": label}}

        ui._select_item("id-x")

        ui.refresh_list.assert_not_called()


if __name__ == "__main__":
    unittest.main()
