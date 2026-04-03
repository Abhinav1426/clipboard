"""Clipboard Manager — entry point with arg parsing, module init, hotkey, and lifecycle."""

import argparse
import atexit
import logging
import sys

import config
from utils.file_utils import ensure_dir


def setup_logging():
    level = logging.DEBUG if config.LOG_DEBUG else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main():
    parser = argparse.ArgumentParser(description="Clipboard Manager")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--classic", action="store_true", help="Use classic Tkinter UI")
    group.add_argument("--modern", action="store_true", help="Use modern CustomTkinter UI")
    args = parser.parse_args()

    setup_logging()
    logger = logging.getLogger(__name__)

    # Determine UI mode
    if args.modern:
        ui_mode = "modern"
    elif args.classic:
        ui_mode = "classic"
    else:
        ui_mode = config.DEFAULT_UI

    # Create data directories
    ensure_dir(config.DATA_DIR)
    ensure_dir(config.ARCHIVE_DIR)

    # Initialize core modules
    from core.history_manager import HistoryManager
    from core.archive_manager import ArchiveManager
    from core.search_engine import SearchEngine
    from core.clipboard_monitor import ClipboardMonitor
    from core.auto_paste import AutoPaste

    history = HistoryManager()
    history.load()

    # Migration from legacy file
    migrated = history.migrate_legacy()
    if migrated:
        logger.info("Migrated %d entries from legacy file", migrated)

    archive = ArchiveManager(history)
    search = SearchEngine(history, archive)
    monitor = ClipboardMonitor(history)
    paste = AutoPaste(monitor)

    # Startup archive rotation check
    if archive.check_and_rotate():
        logger.info("Startup rotation completed")

    # Initialize UI
    if ui_mode == "modern":
        try:
            from ui.modern_ui import ModernUI
            ui = ModernUI(history, archive, search, paste)
        except ImportError:
            logger.warning("customtkinter not available, falling back to classic UI")
            from ui.classic_ui import ClassicUI
            ui = ClassicUI(history, archive, search, paste)
    else:
        from ui.classic_ui import ClassicUI
        ui = ClassicUI(history, archive, search, paste)

    # Register global hotkey
    try:
        import keyboard
        keyboard.add_hotkey(config.HOTKEY, lambda: ui.toggle())
        logger.info("Global hotkey '%s' registered", config.HOTKEY)
    except Exception as e:
        logger.warning("Could not register hotkey '%s': %s", config.HOTKEY, e)

    # Start clipboard monitor
    monitor.start()

    # Graceful shutdown
    def shutdown():
        logger.info("Shutting down...")
        monitor.stop()
        history.save()
        logger.info("Cleanup complete")

    atexit.register(shutdown)

    # Run UI mainloop
    logger.info("Starting Clipboard Manager (%s mode)", ui_mode)
    ui.run()


if __name__ == "__main__":
    main()
