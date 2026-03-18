"""
curator.py — Claude API 필터링 및 요약 모듈.

.env의 TOPICS 키워드를 기준으로 관련 항목을 선별하고 한국어 요약을 작성합니다.
"""

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

import anthropic

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"
DEFAULT_SKILL_PATH = "./SKILL.md"


def load_topics() -> list[str]:
    """
    .env의 TOPICS 값을 파싱해서 반환.
    TOPICS=LLM, multimodal, AI agent, reinforcement learning
    """
    raw = os.getenv("TOPICS", "")
    topics = [t.strip() for t in raw.split(",") if t.strip()]
    return topics


def _build_system_prompt(topics: list[str], skill_path: str) -> str:
    """SKILL.md가 있으면 그걸 쓰고, 없으면 TOPICS 기반으로 자동 생성."""
    p = Path(skill_path)
    if p.exists():
        content = p.read_text(encoding="utf-8").strip()
        if content:
            logger.info(f"SKILL.md 로드: {skill_path}")
            return content

    # SKILL.md 없으면 TOPICS로 자동 생성
    if topics:
        topic_str = ", ".join(topics)
        return f"""당신은 콘텐츠 큐레이터입니다. 수집된 항목들을 검토하고 아래 관심 토픽과 관련된 것만 선별합니다.

관심 토픽: {topic_str}

각 항목에 대해:
- 위 토픽 중 하나 이상과 직접적으로 관련되면 선택 (selected: true)
- 관련 없으면 제외 (selected: false)
- 선택된 항목은 한국어로 2-3문장 요약 작성 (핵심 내용 + 왜 주목할 만한지)
- 어떤 토픽과 관련됐는지 matched_topics에 표시"""
    else:
        return """당신은 AI/ML 콘텐츠 큐레이터입니다.
수집된 항목 중 AI, 머신러닝, 딥러닝과 관련된 주목할 만한 것들을 선별합니다.
선택된 항목은 한국어로 2-3문장 요약을 작성하세요."""


def _build_user_message(items: list[dict], topics: list[str]) -> str:
    topic_hint = f"\n관심 토픽: {', '.join(topics)}\n" if topics else ""

    lines = [
        f"다음 {len(items)}개 항목을 검토해주세요.{topic_hint}",
        "아래 JSON 형식으로만 응답하세요:\n",
        '{"results": [{"index": 0, "selected": true, "matched_topics": ["LLM"], "summary_ko": "한국어 요약."}, ...]}',
        "\n선택되지 않은 항목도 selected: false로 포함해주세요.\n",
        "─" * 40,
    ]

    for i, item in enumerate(items):
        lines.append(f"\n[{i}] {item.get('title', 'N/A')}")
        abstract = item.get("abstract", "").strip()
        if abstract:
            lines.append(f"    {abstract[:500]}{'...' if len(abstract) > 500 else ''}")
        lines.append(f"    출처: {item.get('source_name', '')} | 유형: {item.get('content_type', '')}")

    return "\n".join(lines)


def curate(
    papers: list[dict],
    topics: Optional[list[str]] = None,
    model: str = DEFAULT_MODEL,
    skill_path: str = DEFAULT_SKILL_PATH,
    max_retries: int = 3,
) -> list[dict]:
    """
    항목들을 Claude에 보내고, 토픽 관련 항목만 추려서 반환.

    반환 dict에 추가되는 필드:
        - summary_ko (str)
        - matched_topics (list[str])
    """
    if not papers:
        return []

    if topics is None:
        topics = load_topics()

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")

    client = anthropic.Anthropic(api_key=api_key)
    system_prompt = _build_system_prompt(topics, skill_path)

    logger.info(f"Claude에 {len(papers)}개 항목 전송 (토픽: {topics or '기본'})")

    batch_size = 30
    all_results: dict[int, dict] = {}

    for batch_start in range(0, len(papers), batch_size):
        batch = papers[batch_start : batch_start + batch_size]
        user_message = _build_user_message(batch, topics)

        for attempt in range(1, max_retries + 1):
            try:
                response = client.messages.create(
                    model=model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_message}],
                )
                parsed = _parse_response(response.content[0].text)
                for item in parsed:
                    all_results[batch_start + item.get("index", 0)] = item
                logger.info(f"배치 {batch_start // batch_size + 1}: {len(parsed)}개 평가 완료")
                break

            except anthropic.RateLimitError:
                wait = 2 ** attempt
                logger.warning(f"Rate limit — {wait}초 대기 (시도 {attempt}/{max_retries})")
                time.sleep(wait)
            except (anthropic.APIError, Exception) as e:
                logger.error(f"시도 {attempt} 실패: {e}")
                if attempt == max_retries:
                    raise
                time.sleep(2)

    # 선택된 항목만 추려서 반환
    curated = []
    for idx, item in enumerate(papers):
        result = all_results.get(idx, {})
        if result.get("selected", False):
            curated.append({
                **item,
                "summary_ko": result.get("summary_ko", ""),
                "matched_topics": result.get("matched_topics", []),
            })

    logger.info(f"큐레이션 완료: {len(curated)}/{len(papers)}개 선별 (토픽: {topics})")
    return curated


def _parse_response(raw: str) -> list[dict]:
    text = raw.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0]
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0]
    try:
        return json.loads(text.strip()).get("results", [])
    except json.JSONDecodeError as e:
        logger.error(f"Claude 응답 파싱 실패: {e}")
        return []
