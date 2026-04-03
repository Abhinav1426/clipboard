# Changelog

All notable changes to Clipboard Manager are documented here.

---

## [1.0.1] — 2026-04-03

### Summary
Cross-platform compatibility release. The app now runs on **Windows, macOS, and Linux** without platform-specific hacks.

### Changed

#### Dependency: `keyboard` → `pynput`
- Removed `keyboard==0.13.5` which had no usable macOS support and required root on Linux.
- Added `pynput>=1.7.6` for global hotkeys and key simulation — works on Windows, macOS (with Accessibility permission), and Linux X11.

#### Global hotkey
- Windows / Linux: `Ctrl+Shift+V`
- macOS: `Cmd+Shift+V`
- Hotkey is now defined in `config.py` using pynput's format (`<ctrl>+<shift>+v` / `<cmd>+<shift>+v`) and auto-detected at startup.

#### Auto-paste (`core/auto_paste.py`)
- Replaced `keyboard.send()` with `pynput.keyboard.Controller`.
- Uses `Key.cmd` on macOS and `Key.ctrl` on all other platforms.

#### Thread safety (`ui/base_ui.py`, both UIs)
- Hotkey callbacks from pynput's listener thread now schedule via `root.after(0, ...)` instead of calling Tkinter directly — prevents race conditions on all platforms.
- Added `thread_safe_toggle()` to `BaseUI`; both UIs implement `_schedule_on_main()`.

#### Platform-aware fonts (`config.py`)
| Platform | UI font | Mono font |
|----------|---------|-----------|
| Windows | Segoe UI | Consolas |
| macOS | SF Pro Text | Menlo |
| Linux | Ubuntu | Monospace |
- Both UIs use `config.UI_FONT` and `config.UI_FONT_MONO` instead of hardcoded strings. Tkinter falls back gracefully if the named font is unavailable.

#### Linux scroll events (`ui/classic_ui.py`)
- Added `Button-4` / `Button-5` bindings alongside `MouseWheel` so scrolling works under X11 on Linux.

#### macOS right-click (`ui/classic_ui.py`)
- Added `Button-2` and `Control-Button-1` bindings in addition to `Button-3` for context menus.

#### macOS keyboard shortcuts (both UIs)
- `Cmd+P` / `Cmd+F` on macOS instead of `Ctrl+P` / `Ctrl+F`.

### Fixed
- `TclError: bad screen distance "6 2"` — `pady=(6, 2)` tuple was incorrectly passed to a `tk.Label` constructor instead of its `.pack()` call.

---

## [1.0.0] — 2026-04-03

### Summary
Initial release.

### Features
- Clipboard history tracking with duplicate prevention
- Pin / unpin items (up to 50 pinned entries)
- Archive rotation: keep newest 50 in memory, archive older entries to dated JSON files
- In-memory + archive search with TTL cache (5 minutes)
- Auto-paste: Enter or double-click copies and pastes the item into the active window
- Global hotkey to toggle the window
- Classic Tkinter UI (default) and Modern CustomTkinter UI (`--modern`)
- Atomic JSON persistence with corrupt-file recovery and `.corrupt` backups
- Legacy history migration from `old_versions/clipboard_history.json`
- 82-test suite using Python's built-in `unittest` (no extra dependencies)
