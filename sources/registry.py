"""
sources/registry.py — 활성 소스 목록.

새 소스를 추가하려면:
  1. sources/ 폴더에 파일 생성 (ContentSource 상속)
  2. 아래 ACTIVE_SOURCES 리스트에 인스턴스 추가

content_type 예시: "paper" | "news" | "blog" | "tweet" | "video"
"""

from sources.huggingface import HuggingFaceSource

# ── 활성 소스 목록 ─────────────────────────────────────────────────────────────
ACTIVE_SOURCES = [
    HuggingFaceSource(max_items=20),

    # ── 추가 예시 (주석 해제해서 사용) ────────────────────────────────────────
    # from sources.arxiv import ArxivSource
    # ArxivSource(query="LLM agent reasoning", max_items=10),
    #
    # from sources.techcrunch import TechCrunchSource
    # TechCrunchSource(max_items=10),
    #
    # from sources.ycombinator import HackerNewsSource
    # HackerNewsSource(tag="AI", max_items=15),
]
