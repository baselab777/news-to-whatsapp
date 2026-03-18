"""
sources/base.py — Generic content source interface.

Works for papers, news articles, blog posts, or anything else.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ContentItem:
    """
    A single scraped item — paper, news article, blog post, etc.
    'content_type' is a free-form tag: "paper" | "news" | "blog" | ...
    """
    title: str
    url: str
    source_name: str
    content_type: str = "paper"         # set by each source
    abstract: Optional[str] = None      # body / summary / description
    date: Optional[str] = None          # YYYY-MM-DD
    authors: Optional[list[str]] = field(default_factory=list)
    tags: Optional[list[str]] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "url": self.url,
            "source_name": self.source_name,
            "content_type": self.content_type,
            "abstract": self.abstract or "",
            "date": self.date or datetime.now().strftime("%Y-%m-%d"),
            "authors": self.authors or [],
            "tags": self.tags or [],
        }


class ContentSource(ABC):
    """
    Abstract base for all scrapers.

    Minimal implementation:

        class MySource(ContentSource):
            name = "My Site"
            content_type = "news"    # or "paper", "blog", etc.

            def scrape(self) -> list[dict]:
                return [
                    {
                        "title": "...",
                        "url": "...",
                        "abstract": "...",       # body / description
                        "source_name": self.name,
                        "content_type": self.content_type,
                        "date": "YYYY-MM-DD",    # optional
                        "authors": [],           # optional
                        "tags": [],              # optional
                    }
                ]

    Then register in sources/registry.py.
    """

    name: str = "Unknown"
    content_type: str = "item"

    @abstractmethod
    def scrape(self) -> list[dict]:
        """Return a list of content item dicts."""
        ...


# Backwards-compatible alias
Source = ContentSource
Paper = ContentItem
