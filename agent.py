"""
agent.py — Claude 에이전트 (web_search 툴 포함)

TOPICS 기반으로 Claude가 알아서:
  1. 관련 논문/뉴스 검색
  2. 한국어 요약 작성
  3. 구조화된 결과 반환
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
SKILL_PATH = "./SKILL.md"


def load_topics() -> list[str]:
    raw = os.getenv("TOPICS", "")
    return [t.strip() for t in raw.split(",") if t.strip()]


def _system_prompt(topics: list[str]) -> str:
    # SKILL.md가 있으면 그게 우선
    p = Path(os.getenv("SKILL_FILE_PATH", SKILL_PATH))
    if p.exists():
        content = p.read_text(encoding="utf-8").strip()
        if content:
            return content

    topic_str = ", ".join(topics) if topics else "AI, LLM, machine learning"
    return f"""당신은 AI/ML 리서치 어시스턴트입니다.
web_search 툴로 오늘 날짜 기준 최신 논문과 뉴스를 검색하세요.
관심 토픽: {topic_str}

검색이 끝나면 아래 JSON만 반환하세요 (다른 텍스트 없이):
{{"items": [{{"title": "...", "url": "...", "summary_ko": "2-3문장 한국어 요약.", "matched_topics": ["..."], "date": "YYYY-MM-DD"}}]}}"""


def run(max_items: int = 5) -> list[dict]:
    """에이전트 실행 → 검색+요약된 항목 리스트 반환"""
    topics = load_topics()
    today = datetime.now().strftime("%Y-%m-%d")

    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    logger.info(f"에이전트 시작 — 토픽: {topics or ['기본']}")

    messages = [{
        "role": "user",
        "content": (
            f"오늘({today}) 기준으로 토픽별 최신 항목을 찾아줘. "
            f"최대 {max_items}개를 JSON으로 반환해줘."
        ),
    }]

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=_system_prompt(topics),
            tools=[{"type": "web_search_20250305", "name": "web_search"}],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            for block in response.content:
                if hasattr(block, "text"):
                    return _parse(block.text, today)
            return []

        # 툴 호출 → 결과를 다음 메시지로
        messages.append({"role": "assistant", "content": response.content})
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": getattr(block, "content", ""),
                }
                for block in response.content
                if block.type == "tool_use"
            ],
        })


def _parse(text: str, today: str) -> list[dict]:
    text = text.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]

    try:
        items = json.loads(text.strip()).get("items", [])
    except json.JSONDecodeError as e:
        logger.error(f"JSON 파싱 실패: {e}\n원문: {text[:300]}")
        return []

    result = []
    for item in items:
        if not item.get("title") or not item.get("url"):
            continue
        result.append({
            "title": item["title"],
            "url": item["url"],
            "summary_ko": item.get("summary_ko", ""),
            "matched_topics": item.get("matched_topics", []),
            "date": item.get("date", today),
            "source_name": "Agent",
        })

    logger.info(f"에이전트 완료 — {len(result)}개 항목")
    return result
