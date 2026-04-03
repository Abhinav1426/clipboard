# Clipboard Manager

**Version 1.0.1** | [Changelog](CHANGELOG.md)

A modular Python desktop clipboard manager with clipboard history tracking, pinning, archive rotation, search, and auto-paste. Works on **Windows, macOS, and Linux**. Supports two UIs: a classic Tkinter interface (default) and a modern CustomTkinter interface.

---

## Features

- **Clipboard history** — automatically captures everything you copy
- **Pin / Unpin** — pin important items so they survive rotation (up to 50 pinned)
- **Archive rotation** — older items are automatically archived to JSON files; current list stays lean
- **Search** — search current history or expand to include all archives
- **Auto-paste** — pressing Enter or double-clicking copies and pastes the selected item instantly
- **Global hotkey** — `Ctrl+Shift+V` (Windows/Linux) or `Cmd+Shift+V` (macOS) toggles the window from anywhere
- **Two UIs** — classic Tkinter (default) and modern CustomTkinter
- **Persistent storage** — history survives restarts via atomic JSON writes
- **Corrupt file recovery** — broken JSON files are backed up and skipped gracefully
- **Cross-platform** — Windows 10+, macOS 12+, Linux (X11)

---

## Platform Requirements

| Platform | Tested on | Notes |
|----------|-----------|-------|
| Windows | Windows 10/11 | No admin required for hotkey |
| macOS | macOS 12+ | Needs Accessibility permission for hotkey and auto-paste |
| Linux | Ubuntu 22.04 (X11) | Needs `xclip` or `xsel`; Wayland has limited support |

### Linux clipboard backend
`pyperclip` requires a clipboard backend on Linux:
```bash
sudo apt install xclip     # Debian / Ubuntu
sudo dnf install xclip     # Fedora
sudo pacman -S xclip       # Arch
```

### macOS Accessibility permission
The global hotkey (`Cmd+Shift+V`) and auto-paste simulation require Accessibility access:
> System Settings → Privacy & Security → Accessibility → enable your Terminal or Python app

### Tkinter on Linux
```bash
sudo apt install python3-tk    # Debian / Ubuntu
sudo dnf install python3-tkinter  # Fedora
```

### Tkinter on macOS (Homebrew Python)
```bash
brew install python-tk
```

---

## Installation

### Requirements

- Python 3.11+

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
- `pynput>=1.7.6` — cross-platform global hotkey and key simulation
- `customtkinter>=5.2.1` — modern UI (only needed for `--modern` mode)

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

The window starts **hidden**. Press the global hotkey to show it.

---

## Keyboard Shortcuts

| Key | Windows / Linux | macOS |
|-----|-----------------|-------|
| Toggle window | `Ctrl+Shift+V` | `Cmd+Shift+V` |
| Copy & paste selected | `Enter` | `Enter` |
| Delete selected | `Delete` | `Delete` |
| Pin / Unpin selected | `Ctrl+P` | `Cmd+P` |
| Focus search | `Ctrl+F` | `Cmd+F` |
| Hide window | `Escape` | `Escape` |
| Copy & paste | `Double-click` | `Double-click` |
| Context menu | `Right-click` | `Right-click` or `Ctrl+click` |

---

## Architecture

```
clipboard/
├── main.py                  # Entry point: arg parsing, init, hotkey, lifecycle
├── config.py                # All configuration constants (platform-aware)
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
│   └── auto_paste.py        # Cross-platform paste via pynput Controller
├── ui/
│   ├── base_ui.py           # Abstract base with shared copy/delete/pin/search logic
│   ├── classic_ui.py        # Tkinter UI (cross-platform fonts + scroll events)
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
| `HOTKEY` | `<ctrl>+<shift>+v` / `<cmd>+<shift>+v` | Global toggle hotkey (pynput format, auto-detected) |
| `UI_FONT` | Platform-specific | `Segoe UI` / `SF Pro Text` / `Ubuntu` |
| `UI_FONT_MONO` | Platform-specific | `Consolas` / `Menlo` / `Monospace` |
| `ITEMS_PER_FILE` | `150` | Number of items that triggers archive rotation |
| `MAX_PINNED` | `50` | Maximum number of pinned items |
| `MAX_TEXT_LENGTH` | `250000` | Characters before an entry is truncated |
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

- `id` — UUID, used for all mutations
- `source` — `"external"` (captured), `"migrated"` (legacy import), or `"archive"` (pinned from search)
- `truncated` — only present when text was cut at `MAX_TEXT_LENGTH`

---

## Migration from Legacy Version

If `data/current.json` is empty on startup and `old_versions/clipboard_history.json` exists, entries are automatically imported, assigned new UUIDs, and saved.

---

## Running Tests

No extra dependencies — uses Python's built-in `unittest`:

```bash
python -m unittest discover tests/ -v
```

82 tests covering: text utilities, file I/O, history CRUD, archive rotation, search + cache, and clipboard monitor.

---

## Troubleshooting

**Global hotkey doesn't work on macOS**
- Go to System Settings → Privacy & Security → Accessibility and grant permission to your Terminal app (or the Python binary).

**Global hotkey doesn't work on Linux**
- The hotkey uses `pynput` which requires X11. On Wayland, global hotkeys are blocked by the compositor. Run your session in X11 mode, or launch the app manually each time.

**Auto-paste doesn't work on macOS**
- Same Accessibility permission as the hotkey. `pynput.keyboard.Controller` needs it to inject keystrokes.

**`ModuleNotFoundError: customtkinter`**
- Only needed for `--modern` mode. Install with `pip install customtkinter`. The app falls back to classic UI automatically.

**`pyperclip.PyperclipException` on Linux**
- Install a clipboard backend: `sudo apt install xclip` (Debian/Ubuntu) or equivalent for your distro.

**Clipboard manager doesn't capture text on Linux (Wayland)**
- `pyperclip` has limited Wayland support. Use an X11 session for full functionality.

**Corrupt JSON file**
- The app backs up the broken file as `filename.json.corrupt` and continues with an empty list. You can inspect or delete `.corrupt` files safely.

---

## License

MIT
