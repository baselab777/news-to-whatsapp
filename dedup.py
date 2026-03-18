"""
dedup.py — Deduplication module.

Maintains a JSON log (sent_log.json) of all previously sent items.
Keys are normalized URLs. Auto-cleans entries older than 90 days.
"""

import json
import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse, urlunparse

logger = logging.getLogger(__name__)

DEFAULT_LOG_PATH = "./sent_log.json"
DEFAULT_MAX_AGE_DAYS = 90


def _normalize_url(url: str) -> str:
    """Normalize URL for consistent dedup keying."""
    url = url.strip().rstrip("/")
    try:
        parsed = urlparse(url)
        # lowercase scheme + netloc
        normalized = parsed._replace(
            scheme=parsed.scheme.lower(),
            netloc=parsed.netloc.lower(),
        )
        return urlunparse(normalized)
    except Exception:
        return url.lower()


class DedupLog:
    """
    Manages the sent_log.json file for deduplication.

    Schema:
        {
            "https://huggingface.co/papers/xxxx": {
                "title": "...",
                "sent_at": "2024-01-15T08:00:00",
                "source": "HuggingFace Papers"
            },
            ...
        }
    """

    def __init__(self, log_path: str = DEFAULT_LOG_PATH, max_age_days: int = DEFAULT_MAX_AGE_DAYS):
        self.log_path = Path(log_path)
        self.max_age_days = max_age_days
        self._data: dict[str, dict] = {}
        self._load()

    # ── I/O ──────────────────────────────────────────────────────────────────

    def _load(self):
        if self.log_path.exists():
            try:
                raw = self.log_path.read_text(encoding="utf-8")
                self._data = json.loads(raw)
                logger.debug(f"Loaded {len(self._data)} entries from {self.log_path}")
            except (json.JSONDecodeError, OSError) as e:
                logger.warning(f"Could not load sent log ({e}). Starting fresh.")
                self._data = {}
        else:
            logger.debug("sent_log.json not found — will be created on first save.")
            self._data = {}

    def _save(self):
        try:
            self.log_path.write_text(
                json.dumps(self._data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except OSError as e:
            logger.error(f"Failed to save sent log: {e}")

    # ── Public API ────────────────────────────────────────────────────────────

    def is_sent(self, url: str) -> bool:
        """Return True if this URL has already been sent."""
        return _normalize_url(url) in self._data

    def mark_sent(self, paper: dict):
        """Record a paper as sent."""
        key = _normalize_url(paper.get("url", ""))
        if not key:
            logger.warning("Paper has no URL — skipping dedup record.")
            return
        self._data[key] = {
            "title": paper.get("title", ""),
            "sent_at": datetime.now().isoformat(timespec="seconds"),
            "source": paper.get("source_name", ""),
            "score": paper.get("score", None),
        }

    def mark_sent_batch(self, papers: list[dict]):
        """Record multiple papers as sent, then save once."""
        for paper in papers:
            self.mark_sent(paper)
        self._save()
        logger.info(f"Marked {len(papers)} papers as sent.")

    def filter_new(self, papers: list[dict]) -> list[dict]:
        """Return only papers not already in the sent log."""
        new = [p for p in papers if not self.is_sent(p.get("url", ""))]
        skipped = len(papers) - len(new)
        if skipped:
            logger.info(f"Dedup: skipped {skipped} already-sent items.")
        return new

    def cleanup(self):
        """Remove entries older than max_age_days."""
        cutoff = datetime.now() - timedelta(days=self.max_age_days)
        before = len(self._data)
        to_delete = []

        for url, entry in self._data.items():
            sent_at_str = entry.get("sent_at", "")
            try:
                sent_at = datetime.fromisoformat(sent_at_str)
                if sent_at < cutoff:
                    to_delete.append(url)
            except (ValueError, TypeError):
                pass  # keep malformed entries

        for url in to_delete:
            del self._data[url]

        removed = before - len(self._data)
        if removed:
            logger.info(f"Cleanup: removed {removed} stale entries (>{self.max_age_days} days old).")
            self._save()

    def stats(self) -> dict:
        """Return summary statistics about the log."""
        return {
            "total_entries": len(self._data),
            "log_path": str(self.log_path),
            "max_age_days": self.max_age_days,
        }
