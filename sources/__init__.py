from sources.base import ContentSource, ContentItem, Source, Paper
from sources.huggingface import HuggingFaceSource
from sources.registry import ACTIVE_SOURCES

__all__ = [
    "ContentSource", "ContentItem",
    "HuggingFaceSource",
    "ACTIVE_SOURCES",
    "Source", "Paper",   # backwards-compat aliases
]
