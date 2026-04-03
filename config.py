"""Configuration constants for Clipboard Manager."""

import os
import sys

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
ARCHIVE_DIR = os.path.join(DATA_DIR, "archive")
CURRENT_FILE = os.path.join(DATA_DIR, "current.json")
PINNED_FILE = os.path.join(DATA_DIR, "pinned.json")
LEGACY_HISTORY_FILE = os.path.join(BASE_DIR, "old_versions", "clipboard_history.json")

# UI
DEFAULT_UI = "classic"
AUTO_REFRESH_INTERVAL = 5000  # ms
PREVIEW_MAX_CHARS = 100
PREVIEW_DETAIL_MAX_CHARS = 50000

# Platform-aware hotkey (pynput GlobalHotKeys format)
if sys.platform == "darwin":
    HOTKEY = "<cmd>+<shift>+v"
else:
    HOTKEY = "<ctrl>+<shift>+v"

# Platform-aware fonts (Tkinter falls back gracefully if font not found)
if sys.platform == "darwin":
    UI_FONT = "SF Pro Text"
    UI_FONT_MONO = "Menlo"
elif sys.platform == "win32":
    UI_FONT = "Segoe UI"
    UI_FONT_MONO = "Consolas"
else:  # Linux and other UNIX
    UI_FONT = "Ubuntu"
    UI_FONT_MONO = "Monospace"

# History / Archive
ITEMS_PER_FILE = 150
MAX_ITEMS_IN_MEMORY = 200
MAX_PINNED = 50
MAX_TEXT_LENGTH = 250000

# Monitor
MONITOR_INTERVAL = 0.5  # seconds

# Auto-paste delay (seconds)
PASTE_DELAY = 0.05

# Search
SEARCH_CACHE_TTL = 300  # seconds

# Debug
LOG_DEBUG = False
