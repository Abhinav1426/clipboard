"""Auto-paste: copy text to clipboard and simulate a paste keystroke.

Paste strategy per platform:
  Windows — ctypes SetForegroundWindow restores focus, then pynput Ctrl+V
  macOS   — osascript (built-in), falls back to pynput Cmd+V
  Linux   — xdotool (if installed), falls back to pynput Ctrl+V

Two copy modes:
  copy_to_clipboard_only() — copy + close window, NO paste (Copy button)
  copy_only() + send_paste() — copy + close + paste at cursor (double-click / Enter)
"""

import logging
import subprocess
import sys
import time

import pyperclip
from pynput.keyboard import Controller, Key

import config

logger = logging.getLogger(__name__)

_controller = Controller()


class AutoPaste:
    def __init__(self, clipboard_monitor):
        self._monitor = clipboard_monitor
        self._prev_hwnd = None   # Windows: HWND that had focus before the clipboard manager

    # ── Public API ───────────────────────────────────────────────

    def record_foreground_window(self) -> None:
        """Capture the currently focused window handle (Windows only).
        Call BEFORE showing the clipboard manager so we know which window
        to restore focus to when pasting.
        """
        if sys.platform == "win32":
            try:
                import ctypes
                self._prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
                logger.debug("Recorded foreground HWND: %s", self._prev_hwnd)
            except Exception as e:
                logger.debug("GetForegroundWindow failed: %s", e)

    def copy_to_clipboard_only(self, text: str) -> None:
        """Copy text to clipboard with no paste to follow.
        Used by the Copy button — sets and immediately clears the internal flag
        so the clipboard monitor does not re-capture the item.
        """
        try:
            self._monitor.set_internal_copy()
            pyperclip.copy(text)
        except Exception as e:
            logger.error("Copy to clipboard failed: %s", e)
        finally:
            self._monitor.clear_internal_copy()

    def copy_only(self, text: str) -> None:
        """Write text to clipboard. send_paste() must follow to clear the internal flag."""
        try:
            self._monitor.set_internal_copy()
            pyperclip.copy(text)
        except Exception as e:
            logger.error("Copy to clipboard failed: %s", e)
            self._monitor.clear_internal_copy()

    def send_paste(self) -> None:
        """Restore focus to the recorded window and simulate Ctrl/Cmd+V.
        Call after hide() — safe to run from a background thread.
        """
        try:
            self._restore_focus_and_paste()
        except Exception as e:
            logger.error("send_paste failed: %s", e)
        finally:
            self._monitor.clear_internal_copy()
            self._prev_hwnd = None

    # ── Internal ─────────────────────────────────────────────────

    def _restore_focus_and_paste(self) -> None:
        if sys.platform == "win32":
            self._paste_windows()
        elif sys.platform == "darwin":
            self._paste_macos()
        else:
            self._paste_linux()

    def _paste_windows(self) -> None:
        """Restore the previous foreground window then send Ctrl+V."""
        if self._prev_hwnd:
            try:
                import ctypes
                user32 = ctypes.windll.user32
                # SW_RESTORE (9) un-minimises a window but also de-maximises one.
                # Only call it when the window is actually minimised (IsIconic).
                if user32.IsIconic(self._prev_hwnd):
                    user32.ShowWindow(self._prev_hwnd, 9)   # SW_RESTORE
                user32.SetForegroundWindow(self._prev_hwnd)
                time.sleep(0.1)   # give Windows time to complete the focus transfer
            except Exception as e:
                logger.debug("SetForegroundWindow failed: %s", e)
        else:
            time.sleep(config.PASTE_DELAY + 0.15)

        try:
            with _controller.pressed(Key.ctrl):
                _controller.press("v")
                _controller.release("v")
        except Exception as e:
            logger.error("pynput Ctrl+V failed: %s", e)

    def _paste_macos(self) -> None:
        """Use osascript (built-in on every Mac) to send Cmd+V.
        Falls back to pynput. Requires Accessibility permission either way.
        """
        time.sleep(config.PASTE_DELAY + 0.1)
        try:
            result = subprocess.run(
                [
                    "osascript", "-e",
                    'tell application "System Events" to keystroke "v" using command down',
                ],
                timeout=3,
                capture_output=True,
            )
            if result.returncode != 0:
                raise RuntimeError(result.stderr.decode().strip())
        except Exception as e:
            logger.debug("osascript paste failed (%s), trying pynput", e)
            try:
                with _controller.pressed(Key.cmd):
                    _controller.press("v")
                    _controller.release("v")
            except Exception as e2:
                logger.error("pynput Cmd+V also failed: %s", e2)

    def _paste_linux(self) -> None:
        """Use xdotool (X11) to send Ctrl+V.
        Falls back to pynput if xdotool is not installed.
        """
        time.sleep(config.PASTE_DELAY + 0.1)
        try:
            subprocess.run(
                ["xdotool", "key", "--clearmodifiers", "ctrl+v"],
                timeout=3,
                capture_output=True,
            )
        except FileNotFoundError:
            logger.debug("xdotool not found, trying pynput")
            try:
                with _controller.pressed(Key.ctrl):
                    _controller.press("v")
                    _controller.release("v")
            except Exception as e:
                logger.error("pynput Ctrl+V also failed: %s", e)
        except Exception as e:
            logger.error("xdotool paste failed: %s", e)
