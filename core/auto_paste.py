"""Auto-paste: copy text to clipboard and simulate a paste keystroke.

Paste strategy per platform:
  Windows — ctypes SetForegroundWindow restores focus, then pynput Ctrl+V
  macOS   — osascript (built-in), falls back to pynput Cmd+V
  Linux   — xdotool (if installed), falls back to pynput Ctrl+V

The caller must:
  1. Call record_foreground_window() BEFORE the clipboard manager window appears
  2. Call copy_only(text)
  3. Hide the clipboard manager window
  4. Call send_paste() — which restores focus and fires the keystroke
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
        self._prev_hwnd = None   # Windows: HWND of the window that had focus before us

    # ── Public API ───────────────────────────────────────────────

    def record_foreground_window(self) -> None:
        """Capture the currently focused window handle (Windows only).
        Call this BEFORE the clipboard manager window is shown so we know
        which window to restore focus to when we paste.
        """
        if sys.platform == "win32":
            try:
                import ctypes
                self._prev_hwnd = ctypes.windll.user32.GetForegroundWindow()
                logger.debug("Recorded foreground HWND: %s", self._prev_hwnd)
            except Exception as e:
                logger.debug("GetForegroundWindow failed: %s", e)

    def copy_only(self, text: str) -> None:
        """Write text to clipboard without sending any keystroke."""
        try:
            self._monitor.set_internal_copy()
            pyperclip.copy(text)
        except Exception as e:
            logger.error("Copy to clipboard failed: %s", e)
            self._monitor.clear_internal_copy()

    def send_paste(self) -> None:
        """Restore focus to the previous window and simulate Ctrl/Cmd+V.
        Call this after hide() — runs fine from a background thread.
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
        """Restore the previous foreground window, then send Ctrl+V."""
        if self._prev_hwnd:
            try:
                import ctypes
                # Bring the target window back to the foreground.
                # SW_RESTORE (9) un-minimises if needed.
                ctypes.windll.user32.ShowWindow(self._prev_hwnd, 9)
                ctypes.windll.user32.SetForegroundWindow(self._prev_hwnd)
                time.sleep(0.1)   # give Windows time to complete the focus transfer
            except Exception as e:
                logger.debug("SetForegroundWindow failed: %s", e)
        else:
            # No saved handle — just wait and hope the OS returns focus
            time.sleep(config.PASTE_DELAY + 0.15)

        try:
            with _controller.pressed(Key.ctrl):
                _controller.press("v")
                _controller.release("v")
        except Exception as e:
            logger.error("pynput Ctrl+V failed: %s", e)

    def _paste_macos(self) -> None:
        """Use osascript (built-in on every Mac) to send Cmd+V.
        Falls back to pynput if osascript is unavailable.
        Requires Accessibility permission either way.
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
