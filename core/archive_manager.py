"""Archive manager with rotation-at-threshold and archive stats."""

import logging
import os
from datetime import datetime

import config
from utils.file_utils import ensure_dir, load_json, save_json

logger = logging.getLogger(__name__)


class ArchiveManager:
    def __init__(self, history_manager):
        self._history = history_manager
        ensure_dir(config.ARCHIVE_DIR)

    def check_and_rotate(self) -> bool:
        """Check if rotation is needed and perform it. Returns True if rotated."""
        if self._history.count() >= config.ITEMS_PER_FILE:
            return self.rotate_history()
        return False

    def rotate_history(self) -> bool:
        """Keep newest 50 in current, archive the rest."""
        lock = self._history.get_lock()
        with lock:
            current = self._history.get_current_items_ref()
            if len(current) < config.ITEMS_PER_FILE:
                return False

            keep = 50
            to_archive = current[keep:]
            del current[keep:]

            if not to_archive:
                return False

            filename = self.create_archive_filename()
            archive_path = os.path.join(config.ARCHIVE_DIR, filename)

            if save_json(archive_path, to_archive):
                self._history._save_unlocked()
                logger.info(
                    "Rotated %d items to %s, kept %d",
                    len(to_archive), filename, len(current),
                )
                return True
            else:
                # Restore on failure
                current.extend(to_archive)
                logger.error("Failed to save archive, rotation aborted")
                return False

    @staticmethod
    def create_archive_filename() -> str:
        return datetime.now().strftime("history_%Y%m%d_%H%M%S.json")

    def get_archive_files(self) -> list[str]:
        """Return sorted list of archive filenames (newest first)."""
        try:
            files = [
                f for f in os.listdir(config.ARCHIVE_DIR)
                if f.startswith("history_") and f.endswith(".json")
            ]
            files.sort(reverse=True)
            return files
        except OSError:
            return []

    def load_archive(self, filename: str) -> list[dict]:
        """Load entries from a specific archive file."""
        path = os.path.join(config.ARCHIVE_DIR, filename)
        return load_json(path)

    def get_archive_stats(self) -> dict:
        """Return stats about archives."""
        files = self.get_archive_files()
        total_items = 0
        for f in files:
            data = self.load_archive(f)
            total_items += len(data)
        return {
            "file_count": len(files),
            "total_items": total_items,
        }
