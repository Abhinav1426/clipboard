"""Text utility functions for Clipboard Manager."""

import hashlib
import re


def truncate(text: str, max_len: int) -> tuple[str, bool]:
    """Truncate text to max_len. Returns (text, was_truncated)."""
    if len(text) <= max_len:
        return text, False
    return text[:max_len], True


def is_empty_or_whitespace(text: str) -> bool:
    """Check if text is empty or only whitespace."""
    return not text or text.isspace()


def get_preview(text: str, max_chars: int = 100) -> str:
    """Get a preview of text: collapse whitespace, truncate with '...'."""
    collapsed = re.sub(r"\s+", " ", text).strip()
    if len(collapsed) <= max_chars:
        return collapsed
    return collapsed[:max_chars] + "..."


def content_hash(text: str) -> str:
    """Return MD5 hex digest of text."""
    return hashlib.md5(text.encode("utf-8", errors="replace")).hexdigest()
