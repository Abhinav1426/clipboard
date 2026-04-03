"""History manager with thread-safe CRUD, pin/unpin, duplicate detection, and migration."""

import logging
import threading
import uuid
from datetime import datetime, timezone

import config
from utils.file_utils import load_json, save_json
from utils.text_utils import truncate, is_empty_or_whitespace

logger = logging.getLogger(__name__)


class HistoryManager:
    def __init__(self):
        self._lock = threading.Lock()
        self._current: list[dict] = []
        self._pinned: list[dict] = []

    # ── Load / Save ──────────────────────────────────────────────

    def load(self) -> None:
        with self._lock:
            self._current = load_json(config.CURRENT_FILE)
            self._pinned = load_json(config.PINNED_FILE)
            logger.info(
                "Loaded %d current, %d pinned items",
                len(self._current), len(self._pinned),
            )

    def save(self) -> None:
        with self._lock:
            self._save_unlocked()

    def _save_unlocked(self) -> None:
        """Save without acquiring lock (caller must hold lock)."""
        save_json(config.CURRENT_FILE, self._current)
        save_json(config.PINNED_FILE, self._pinned)

    # ── Query ────────────────────────────────────────────────────

    def get_all_items(self) -> list[dict]:
        with self._lock:
            return list(self._pinned) + list(self._current)

    def get_current_items(self) -> list[dict]:
        with self._lock:
            return list(self._current)

    def get_pinned_items(self) -> list[dict]:
        with self._lock:
            return list(self._pinned)

    def get_current_items_ref(self) -> list[dict]:
        """Return direct reference to current list (for archive manager)."""
        return self._current

    def get_lock(self) -> threading.Lock:
        return self._lock

    def count(self) -> int:
        with self._lock:
            return len(self._current)

    def pinned_count(self) -> int:
        with self._lock:
            return len(self._pinned)

    def total_count(self) -> int:
        with self._lock:
            return len(self._current) + len(self._pinned)

    def get_by_id(self, entry_id: str) -> dict | None:
        with self._lock:
            for item in self._pinned + self._current:
                if item.get("id") == entry_id:
                    return dict(item)
            return None

    def is_duplicate(self, text: str) -> bool:
        """Check if text duplicates recent entries or any pinned entry."""
        with self._lock:
            # Check all pinned
            for item in self._pinned:
                if item.get("text") == text:
                    return True
            # Check last 5 current
            for item in self._current[:5]:
                if item.get("text") == text:
                    return True
            return False

    # ── Mutation ─────────────────────────────────────────────────

    def add(self, text: str, source: str = "external") -> dict | None:
        if is_empty_or_whitespace(text):
            return None

        truncated_text, was_truncated = truncate(text, config.MAX_TEXT_LENGTH)

        entry = {
            "id": str(uuid.uuid4()),
            "text": truncated_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "pinned": False,
            "source": source,
        }
        if was_truncated:
            entry["truncated"] = True

        with self._lock:
            self._current.insert(0, entry)
            # Enforce memory limit
            if len(self._current) > config.MAX_ITEMS_IN_MEMORY:
                self._current = self._current[: config.MAX_ITEMS_IN_MEMORY]
            self._save_unlocked()

        logger.debug("Added entry %s", entry["id"])
        return entry

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            for lst in (self._current, self._pinned):
                for i, item in enumerate(lst):
                    if item.get("id") == entry_id:
                        lst.pop(i)
                        self._save_unlocked()
                        return True
            return False

    def toggle_pin(self, entry_id: str) -> bool:
        with self._lock:
            # Check if currently pinned → unpin
            for i, item in enumerate(self._pinned):
                if item.get("id") == entry_id:
                    item["pinned"] = False
                    self._pinned.pop(i)
                    self._current.insert(0, item)
                    self._save_unlocked()
                    return True

            # Check if in current → pin
            for i, item in enumerate(self._current):
                if item.get("id") == entry_id:
                    if len(self._pinned) >= config.MAX_PINNED:
                        logger.warning("Max pinned items reached (%d)", config.MAX_PINNED)
                        return False
                    item["pinned"] = True
                    self._current.pop(i)
                    self._pinned.insert(0, item)
                    self._save_unlocked()
                    return True

            return False

    def pin_from_external(self, text: str, timestamp: str = None) -> dict | None:
        """Pin an entry from archive search results."""
        with self._lock:
            if len(self._pinned) >= config.MAX_PINNED:
                logger.warning("Max pinned items reached")
                return None

            truncated_text, was_truncated = truncate(text, config.MAX_TEXT_LENGTH)
            entry = {
                "id": str(uuid.uuid4()),
                "text": truncated_text,
                "timestamp": timestamp or datetime.now(timezone.utc).isoformat(),
                "pinned": True,
                "source": "archive",
            }
            if was_truncated:
                entry["truncated"] = True

            self._pinned.insert(0, entry)
            self._save_unlocked()
            return entry

    def clear_all(self) -> None:
        """Clear all non-pinned items."""
        with self._lock:
            self._current.clear()
            self._save_unlocked()

    # ── Migration ────────────────────────────────────────────────

    def migrate_legacy(self) -> int:
        """Import from legacy file if current history is empty. Returns count imported."""
        import os
        with self._lock:
            if self._current or self._pinned:
                return 0
            if not os.path.exists(config.LEGACY_HISTORY_FILE):
                return 0

            legacy_data = load_json(config.LEGACY_HISTORY_FILE)
            if not legacy_data:
                return 0

            count = 0
            for old_entry in legacy_data:
                text = old_entry.get("text", old_entry.get("content", ""))
                if is_empty_or_whitespace(text):
                    continue
                truncated_text, was_truncated = truncate(text, config.MAX_TEXT_LENGTH)
                entry = {
                    "id": str(uuid.uuid4()),
                    "text": truncated_text,
                    "timestamp": old_entry.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "pinned": old_entry.get("pinned", False),
                    "source": "migrated",
                }
                if was_truncated:
                    entry["truncated"] = True

                if entry["pinned"] and len(self._pinned) < config.MAX_PINNED:
                    self._pinned.append(entry)
                else:
                    entry["pinned"] = False
                    self._current.append(entry)
                count += 1

            if count:
                self._save_unlocked()
                logger.info("Migrated %d entries from legacy file", count)
            return count
