"""Auto-paste: copy text to clipboard and simulate paste shortcut.

Uses pynput.keyboard.Controller for cross-platform key simulation:
  - Windows : Ctrl+V
  - macOS   : Cmd+V  (requires Accessibility permission)
  - Linux   : Ctrl+V (requires X11; limited on Wayland)
"""

import logging
import sys
import time

import pyperclip
from pynput.keyboard import Controller, Key

import config

logger = logging.getLogger(__name__)

_controller = Controller()


def _get_paste_modifier() -> Key:
    return Key.cmd if sys.platform == "darwin" else Key.ctrl


class AutoPaste:
    def __init__(self, clipboard_monitor):
        self._monitor = clipboard_monitor

    def copy_and_paste(self, text: str) -> None:
        """Copy text to clipboard and simulate paste into the active window."""
        try:
            self._monitor.set_internal_copy()
            pyperclip.copy(text)
            time.sleep(config.PASTE_DELAY)
            self._send_paste()
            time.sleep(config.PASTE_DELAY)
        except Exception as e:
            logger.error("Auto-paste failed: %s", e)
        finally:
            self._monitor.clear_internal_copy()

    @staticmethod
    def _send_paste() -> None:
        mod = _get_paste_modifier()
        with _controller.pressed(mod):
            _controller.press("v")
            _controller.release("v")
