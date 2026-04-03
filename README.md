# Clipboard Manager

A modular Python desktop clipboard manager with clipboard history tracking, pinning, archive rotation, search, and auto-paste. Supports two UIs: a classic Tkinter interface (default) and a modern CustomTkinter interface.

---

## Features

- **Clipboard history** — automatically captures everything you copy
- **Pin / Unpin** — pin important items so they survive rotation (up to 50 pinned)
- **Archive rotation** — older items are automatically archived to JSON files; current list stays lean
- **Search** — search current history or expand to include all archives
- **Auto-paste** — pressing Enter or double-clicking copies and pastes the selected item instantly
- **Global hotkey** — `Alt+V` toggles the window from anywhere
- **Two UIs** — classic Tkinter (default) and modern CustomTkinter
- **Persistent storage** — history survives restarts via atomic JSON writes
- **Corrupt file recovery** — broken JSON files are backed up and skipped gracefully

---

## Installation

### Requirements

- Python 3.11+
- Windows (primary target; macOS/Linux compatible where noted)

### Steps

```bash
# Clone the repository
git clone https://github.com/Abhinav1426/clipboard.git
cd clipboard

# Install dependencies
pip install -r requirements.txt
```

`requirements.txt` installs:
- `pyperclip==1.8.2` — cross-platform clipboard access
- `keyboard==0.13.5` — global hotkey and auto-paste simulation
- `customtkinter>=5.2.1` — modern UI (only needed for `--modern` mode)

> **Windows note:** `keyboard` requires running as Administrator for global hotkeys to register. If you cannot run as admin, the app still works — the hotkey simply won't be available.

---

## Usage

```bash
# Launch with classic Tkinter UI (default)
python main.py

# Launch with classic UI explicitly
python main.py --classic

# Launch with modern CustomTkinter UI
python main.py --modern
```

The window starts **hidden**. Press `Alt+V` to show it (or toggle it).

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| `Alt+V` | Toggle window (global hotkey) |
| `Enter` | Copy selected item and paste into active window |
| `Delete` | Delete selected item |
| `Ctrl+P` | Pin / Unpin selected item |
| `Ctrl+F` | Focus the search field |
| `Escape` | Hide window |
| `Double-click` | Copy and paste selected item |
| `Right-click` | Context menu (Copy, Pin/Unpin, Delete) |

---

## Architecture

```
clipboard/
├── main.py                  # Entry point: arg parsing, init, hotkey, lifecycle
├── config.py                # All configuration constants
├── requirements.txt
├── README.md
├── data/
│   ├── current.json         # Active (non-pinned) history
│   ├── pinned.json          # Pinned items
│   └── archive/             # Timestamped archive files
├── core/
│   ├── history_manager.py   # Thread-safe CRUD, pin/unpin, duplicate detection
│   ├── archive_manager.py   # Rotation logic and archive file management
│   ├── search_engine.py     # In-memory + archive search with TTL cache
│   ├── clipboard_monitor.py # Polling thread that watches the clipboard
│   └── auto_paste.py        # Copy-to-clipboard + paste shortcut simulation
├── ui/
│   ├── base_ui.py           # Abstract base with shared copy/delete/pin/search logic
│   ├── classic_ui.py        # Tkinter UI implementation
│   └── modern_ui.py         # CustomTkinter UI implementation
├── utils/
│   ├── file_utils.py        # Atomic JSON save, corrupt recovery, ensure_dir
│   └── text_utils.py        # Truncate, preview, hash, whitespace helpers
└── tests/
    ├── test_text_utils.py
    ├── test_file_utils.py
    ├── test_history_manager.py
    ├── test_archive_manager.py
    ├── test_search_engine.py
    └── test_clipboard_monitor.py
```

---

## Configuration

All constants live in `config.py`. Key settings:

| Constant | Default | Description |
|----------|---------|-------------|
| `DEFAULT_UI` | `"classic"` | Which UI to use when no flag is passed |
| `HOTKEY` | `"alt+v"` | Global toggle hotkey |
| `ITEMS_PER_FILE` | `150` | Number of items that triggers archive rotation |
| `MAX_PINNED` | `50` | Maximum number of pinned items |
| `MAX_TEXT_LENGTH` | `150000` | Characters before an entry is truncated |
| `MAX_ITEMS_IN_MEMORY` | `200` | Cap on current (non-pinned) items in memory |
| `MONITOR_INTERVAL` | `0.5` | Clipboard poll frequency in seconds |
| `PASTE_DELAY` | `0.05` | Delay (seconds) around the paste shortcut |
| `SEARCH_CACHE_TTL` | `300` | Archive search cache lifetime in seconds |
| `AUTO_REFRESH_INTERVAL` | `5000` | UI list refresh interval in milliseconds |
| `PREVIEW_MAX_CHARS` | `100` | Characters shown in the list preview |
| `LOG_DEBUG` | `False` | Enable verbose debug logging |

---

## Archive Behavior

When the number of non-pinned items reaches `ITEMS_PER_FILE` (default 150):

1. The newest 50 items stay in `data/current.json`.
2. The remaining older items are written to `data/archive/history_YYYYMMDD_HHMMSS.json`.
3. Pinned items are **never** rotated or archived.

Archive files accumulate indefinitely. Searching with "Search archives" enabled searches all of them with a TTL cache (default 5 minutes) to keep it fast.

---

## Data Format

Each clipboard entry is a JSON object:

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "text": "the copied text content",
  "timestamp": "2025-03-08T15:55:20.123456+00:00",
  "pinned": false,
  "source": "external",
  "truncated": true
}
```

- `id` — UUID, used for all mutations (never timestamp-based)
- `source` — `"external"` (captured), `"migrated"` (from legacy import), or `"archive"` (pinned from archive result)
- `truncated` — only present when text was cut at `MAX_TEXT_LENGTH`

---

## Migration from Legacy Version

If `data/current.json` is empty on startup and a file exists at `old_versions/clipboard_history.json`, the app automatically imports entries from the old format, assigns new UUIDs, and saves them.

---

## Running Tests

No extra dependencies needed — uses Python's built-in `unittest`:

```bash
python -m unittest discover tests/ -v
```

82 tests covering: text utilities, file I/O, history CRUD, archive rotation, search + cache, and clipboard monitor.

---

## Troubleshooting

**Hotkey `Alt+V` doesn't work**
- On Windows, `keyboard` requires Administrator privileges. Run your terminal as Administrator.
- If you cannot use admin mode, you can open the window by launching `python main.py` directly each time.

**`ModuleNotFoundError: customtkinter`**
- Only needed for `--modern` mode. Install with `pip install customtkinter`.
- The app automatically falls back to classic UI if customtkinter is missing.

**`pyperclip.PyperclipException` on Linux/macOS**
- Install a clipboard backend: `sudo apt install xclip` (Linux) or `brew install pbcopy` (macOS).

**Corrupt JSON file**
- The app backs up the broken file as `filename.json.corrupt` and continues with an empty list.
- You can inspect or delete `.corrupt` files safely.

**App freezes on startup**
- This can happen if `pyperclip.paste()` hangs (e.g., clipboard held by another process). Restart the other process and try again.

---

## License

MIT
