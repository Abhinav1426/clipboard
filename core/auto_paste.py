"""Auto-paste: copy text to clipboard and simulate a paste keystroke.

Paste strategy per platform:
  Windows — SetForegroundWindow BEFORE hide() (while we still own focus),
            then pynput Ctrl+V fires into the already-focused window.
  macOS   — osascript (built-in), falls back to pynput Cmd+V
  Linux   — xdotool (if installed), falls back to pynput Ctrl+V

Two copy modes:
  copy_to_clipboard_only() — copy + close window, NO paste (Copy button)
  copy_only() + restore_focus() + send_paste() — copy + paste at cursor
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

    def restore_focus(self) -> None:
        """Windows only: call SetForegroundWindow BEFORE hiding the clipboard manager.

        SetForegroundWindow only works while our process still owns the foreground.
        Once our window is hidden/withdrawn, Windows removes that privilege and the
        call silently fails. Call this first, then hide(), then send_paste().
        """
        if sys.platform != "win32" or not self._prev_hwnd:
            return
        try:
            import ctypes
            user32 = ctypes.windll.user32
            # Un-minimise only if actually minimised — SW_RESTORE de-maximises too.
            if user32.IsIconic(self._prev_hwnd):
                user32.ShowWindow(self._prev_hwnd, 9)   # SW_RESTORE
            user32.SetForegroundWindow(self._prev_hwnd)
            logger.debug("Focus restored to HWND %s", self._prev_hwnd)
        except Exception as e:
            logger.debug("restore_focus failed: %s", e)

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
        """Simulate Ctrl/Cmd+V in the previously focused window.
        On Windows, focus was already restored by restore_focus() before hide().
        Safe to call from a background thread.
        """
        try:
            self._do_paste()
        except Exception as e:
            logger.error("send_paste failed: %s", e)
        finally:
            self._monitor.clear_internal_copy()
            self._prev_hwnd = None

    # ── Internal ─────────────────────────────────────────────────

    def _do_paste(self) -> None:
        if sys.platform == "win32":
            self._paste_windows()
        elif sys.platform == "darwin":
            self._paste_macos()
        else:
            self._paste_linux()

    def _paste_windows(self) -> None:
        """Send Ctrl+V. Focus was already restored by restore_focus() before hide()."""
        # Give Windows time to finish the focus transition started by restore_focus().
        time.sleep(config.PASTE_DELAY + 0.1)
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
