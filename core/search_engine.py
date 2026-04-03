"""Search engine with current/archive search and TTL cache."""

import logging
import time

import config
from utils.text_utils import get_preview

logger = logging.getLogger(__name__)


class SearchEngine:
    def __init__(self, history_manager, archive_manager):
        self._history = history_manager
        self._archive = archive_manager
        self._cache: dict[str, tuple[float, list[dict]]] = {}

    def get_search_results(self, query: str, include_archives: bool = False) -> list[dict]:
        if not query or not query.strip():
            return []
        if include_archives:
            return self.search_all(query)
        return self.search_current(query)

    def search_current(self, query: str) -> list[dict]:
        """Search current + pinned items in memory."""
        query_lower = query.lower()
        results = []
        for item in self._history.get_all_items():
            text = item.get("text", "")
            if query_lower in text.lower():
                results.append({
                    **item,
                    "source_file": "memory",
                    "match_preview": get_preview(text, config.PREVIEW_MAX_CHARS),
                })
        return results

    def search_all(self, query: str) -> list[dict]:
        """Search current + pinned + all archives."""
        results = self.search_current(query)

        # Search archives (with caching)
        for filename in self._archive.get_archive_files():
            archive_results = self.search_archive(query, filename)
            results.extend(archive_results)

        return results

    def search_archive(self, query: str, filename: str) -> list[dict]:
        """Search a single archive file with TTL cache."""
        cache_key = f"{query}:{filename}"

        # Check cache
        if cache_key in self._cache:
            cached_time, cached_results = self._cache[cache_key]
            if time.time() - cached_time < config.SEARCH_CACHE_TTL:
                return cached_results

        query_lower = query.lower()
        results = []
        entries = self._archive.load_archive(filename)
        for item in entries:
            text = item.get("text", "")
            if query_lower in text.lower():
                results.append({
                    **item,
                    "source_file": filename,
                    "match_preview": get_preview(text, config.PREVIEW_MAX_CHARS),
                })

        self._cache[cache_key] = (time.time(), results)
        return results

    def clear_cache(self) -> None:
        self._cache.clear()
