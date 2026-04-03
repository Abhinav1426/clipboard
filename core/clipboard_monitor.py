"""Clipboard monitor with polling thread and duplicate prevention."""

import logging
import threading
import time

import pyperclip

import config
from utils.text_utils import is_empty_or_whitespace

logger = logging.getLogger(__name__)


class ClipboardMonitor:
    def __init__(self, history_manager):
        self._history = history_manager
        self._running = False
        self._thread: threading.Thread | None = None
        self._internal_copy = False
        self._last_content = ""

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        # Capture current clipboard so we don't add it on startup
        try:
            self._last_content = pyperclip.paste() or ""
        except Exception:
            self._last_content = ""
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info("Clipboard monitor started")

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        logger.info("Clipboard monitor stopped")

    def set_internal_copy(self) -> None:
        self._internal_copy = True

    def clear_internal_copy(self) -> None:
        self._internal_copy = False

    def is_internal_copy(self) -> bool:
        return self._internal_copy

    def _monitor_loop(self) -> None:
        while self._running:
            try:
                self._check_clipboard()
            except Exception as e:
                logger.debug("Monitor error: %s", e)
            time.sleep(config.MONITOR_INTERVAL)

    def _check_clipboard(self) -> None:
        try:
            content = pyperclip.paste()
        except Exception:
            return

        if not content or content == self._last_content:
            return

        self._last_content = content

        # Skip self-generated copies
        if self._internal_copy:
            return

        if is_empty_or_whitespace(content):
            return

        # Duplicate check
        if self._history.is_duplicate(content):
            return

        self._history.add(content, source="external")
        logger.debug("Captured new clipboard content (%d chars)", len(content))
