"""File utility functions for Clipboard Manager."""

import json
import logging
import os
import shutil
import tempfile

logger = logging.getLogger(__name__)


def ensure_dir(path: str) -> None:
    """Create directory if it doesn't exist."""
    os.makedirs(path, exist_ok=True)


def load_json(path: str) -> list:
    """Load JSON array from file. Returns [] if missing or corrupt."""
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            return data
        logger.warning("JSON file %s is not a list, returning []", path)
        return []
    except (json.JSONDecodeError, ValueError) as e:
        logger.error("Corrupt JSON file %s: %s", path, e)
        # Backup corrupt file
        corrupt_path = path + ".corrupt"
        try:
            shutil.copy2(path, corrupt_path)
            logger.info("Backed up corrupt file to %s", corrupt_path)
        except OSError:
            pass
        return []
    except OSError as e:
        logger.error("Cannot read %s: %s", path, e)
        return []


def save_json(path: str, data: list) -> bool:
    """Atomically save data as JSON. Returns True on success."""
    dir_path = os.path.dirname(path)
    try:
        ensure_dir(dir_path)
        fd, tmp_path = tempfile.mkstemp(suffix=".tmp", dir=dir_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            # On Windows, need to remove target first
            if os.path.exists(path):
                os.replace(tmp_path, path)
            else:
                os.rename(tmp_path, path)
        except Exception:
            # Clean up temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise
        return True
    except OSError as e:
        logger.error("Failed to save %s: %s", path, e)
        return False
