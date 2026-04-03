"""Auto-paste: copy text to clipboard and simulate paste shortcut."""

import logging
import time

import keyboard
import pyperclip

import config

logger = logging.getLogger(__name__)


class AutoPaste:
    def __init__(self, clipboard_monitor):
        self._monitor = clipboard_monitor

    def copy_and_paste(self, text: str) -> None:
        """Copy text to clipboard and simulate paste into the active window."""
        try:
            self._monitor.set_internal_copy()
            pyperclip.copy(text)
            time.sleep(config.PASTE_DELAY)
            keyboard.send(config.PASTE_SHORTCUT)
            time.sleep(config.PASTE_DELAY)
        except Exception as e:
            logger.error("Auto-paste failed: %s", e)
        finally:
            self._monitor.clear_internal_copy()
