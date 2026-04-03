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
HOTKEY = "win+v"
AUTO_REFRESH_INTERVAL = 5000  # ms
PREVIEW_MAX_CHARS = 100
PREVIEW_DETAIL_MAX_CHARS = 50000

# History / Archive
ITEMS_PER_FILE = 150
MAX_ITEMS_IN_MEMORY = 200
MAX_PINNED = 50
MAX_TEXT_LENGTH = 250000

# Monitor
MONITOR_INTERVAL = 0.5  # seconds

# Auto-paste
PASTE_DELAY = 0.05
PASTE_SHORTCUT = "command+v" if sys.platform == "darwin" else "ctrl+v"

# Search
SEARCH_CACHE_TTL = 300  # seconds

# Debug
LOG_DEBUG = False
