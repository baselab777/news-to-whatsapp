"""
HuggingFace Daily Papers scraper.
Target: https://huggingface.co/papers
"""

import logging
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from sources.base import ContentSource

logger = logging.getLogger(__name__)

HF_PAPERS_URL = "https://huggingface.co/papers"
HF_BASE_URL = "https://huggingface.co"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}


class HuggingFaceSource(ContentSource):
    """Scrapes trending papers from HuggingFace Daily Papers."""

    name = "HuggingFace Papers"
    content_type = "paper"

    def __init__(self, max_items: int = 20, timeout: int = 15):
        self.max_items = max_items
        self.timeout = timeout

    def scrape(self) -> list[dict]:
        """Scrape trending papers from HuggingFace."""
        logger.info(f"[{self.name}] Starting scrape of {HF_PAPERS_URL}")
        try:
            resp = httpx.get(HF_PAPERS_URL, headers=HEADERS, timeout=self.timeout, follow_redirects=True)
            resp.raise_for_status()
        except httpx.HTTPError as e:
            logger.error(f"[{self.name}] HTTP error fetching page: {e}")
            return []
        except Exception as e:
            logger.error(f"[{self.name}] Unexpected error: {e}")
            return []

        items = self._parse(resp.text)
        logger.info(f"[{self.name}] Found {len(items)} items")
        return items[: self.max_items]

    def _parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "html.parser")
        results = []
        today = datetime.now().strftime("%Y-%m-%d")

        articles = soup.find_all("article")
        if not articles:
            articles = soup.select("div.paper-card, div[class*='paper']")

        for article in articles:
            try:
                item = self._parse_article(article, today)
                if item:
                    results.append(item)
            except Exception as e:
                logger.debug(f"[{self.name}] Failed to parse article: {e}")
                continue

        return results

    def _parse_article(self, article, today: str) -> dict | None:
        # Title & URL — primary <a> with h3 or similar heading
        title_tag = article.find(["h3", "h2", "h1"])
        link_tag = article.find("a", href=True)

        if not title_tag or not link_tag:
            return None

        title = title_tag.get_text(strip=True)
        if not title:
            return None

        href = link_tag["href"]
        url = href if href.startswith("http") else f"{HF_BASE_URL}{href}"

        # Abstract / summary — look for <p> tags inside the article
        abstract = ""
        p_tags = article.find_all("p")
        for p in p_tags:
            text = p.get_text(strip=True)
            if len(text) > 50:  # skip very short snippets
                abstract = text
                break

        # Authors — small text, often in spans
        authors = []
        author_section = article.find(class_=lambda c: c and "author" in c.lower())
        if author_section:
            for a in author_section.find_all(["span", "a"]):
                name = a.get_text(strip=True)
                if name and len(name) < 60:
                    authors.append(name)

        # Date — look for time tags or date strings
        date_str = today
        time_tag = article.find("time")
        if time_tag:
            dt = time_tag.get("datetime", "")
            if dt:
                try:
                    date_str = dt[:10]  # YYYY-MM-DD
                except Exception:
                    pass

        return {
            "title": title,
            "url": url,
            "abstract": abstract,
            "source_name": self.name,
            "content_type": self.content_type,
            "date": date_str,
            "authors": authors,
            "tags": [],
        }
