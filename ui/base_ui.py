"""Abstract base UI with shared concrete logic for clipboard manager."""

import logging
import threading
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# Delay (seconds) between hide() and send_paste().
# On Windows focus is restored explicitly via SetForegroundWindow so 0.05s is enough.
# On macOS/Linux the platform paste methods add their own sleep internally.
_FOCUS_RETURN_DELAY = 0.05


class BaseUI(ABC):
    def __init__(self, history_manager, archive_manager, search_engine, auto_paste):
        self.history = history_manager
        self.archive = archive_manager
        self.search = search_engine
        self.auto_paste = auto_paste
        self._selected_id: str | None = None

    # ── Abstract methods ─────────────────────────────────────────

    @abstractmethod
    def setup_window(self):
        ...

    @abstractmethod
    def create_widgets(self):
        ...

    @abstractmethod
    def bind_events(self):
        ...

    @abstractmethod
    def refresh_list(self):
        ...

    @abstractmethod
    def show(self):
        ...

    @abstractmethod
    def hide(self):
        ...

    @abstractmethod
    def run(self):
        ...

    @abstractmethod
    def _schedule_on_main(self, callback):
        """Schedule callback on the UI main thread (safe to call from any thread)."""
        ...

    # ── Shared concrete logic ────────────────────────────────────

    def thread_safe_toggle(self) -> None:
        """Toggle visibility from any thread (hotkey callback safe).

        Called from pynput's listener thread at the moment the hotkey fires —
        BEFORE the clipboard manager window is shown — so the previous app
        still owns focus. We record that window handle here so paste can
        restore focus to it later.
        """
        self.auto_paste.record_foreground_window()
        self._schedule_on_main(self.toggle)

    def get_selected_id(self) -> str | None:
        return self._selected_id

    def set_selected_id(self, entry_id: str | None) -> None:
        self._selected_id = entry_id

    def copy_to_clipboard(self) -> None:
        """Copy selected item to clipboard and close — no auto-paste. Used by the Copy button."""
        entry_id = self.get_selected_id()
        if not entry_id:
            return
        item = self.history.get_by_id(entry_id)
        if item:
            self.auto_paste.copy_to_clipboard_only(item["text"])
            self.hide()

    def copy_selected(self) -> None:
        """Copy + paste at cursor. Used by double-click and Enter."""
        entry_id = self.get_selected_id()
        if not entry_id:
            return
        item = self.history.get_by_id(entry_id)
        if item:
            # 1. Copy to clipboard
            self.auto_paste.copy_only(item["text"])
            # 2. Hide window so the previous app regains focus
            self.hide()
            # 3. After the OS returns focus to the previous window, send paste.
            #    A daemon timer keeps this off the UI thread and auto-exits with the app.
            t = threading.Timer(_FOCUS_RETURN_DELAY, self.auto_paste.send_paste)
            t.daemon = True
            t.start()

    def delete_selected(self) -> None:
        entry_id = self.get_selected_id()
        if not entry_id:
            return
        self.history.delete(entry_id)
        self._selected_id = None
        self.refresh_list()

    def pin_selected(self) -> None:
        entry_id = self.get_selected_id()
        if not entry_id:
            return
        self.history.toggle_pin(entry_id)
        self.refresh_list()

    def do_search(self, query: str, include_archives: bool = False) -> list[dict]:
        if not query.strip():
            return self.history.get_all_items()
        return self.search.get_search_results(query, include_archives)

    def clear_all(self) -> None:
        self.history.clear_all()
        self._selected_id = None
        self.refresh_list()

    def build_status_text(self) -> str:
        current_count = self.history.count()
        pinned_count = self.history.pinned_count()
        stats = self.archive.get_archive_stats()
        total = current_count + pinned_count + stats["total_items"]
        return (
            f"{current_count} items | {pinned_count} pinned | "
            f"{stats['file_count']} archives | {total} total"
        )
