"""
sender.py — WhatsApp message sender via whatsapp-web.js Node.js bridge.

The Node.js script (whatsapp_bridge/index.js) handles the actual
WhatsApp connection. This module spawns it as a subprocess and
communicates via stdin/stdout JSON messages.
"""

import json
import logging
import os
import subprocess
import sys
import time
from pathlib import Path

logger = logging.getLogger(__name__)

BRIDGE_DIR = Path(__file__).parent / "whatsapp_bridge"
BRIDGE_SCRIPT = BRIDGE_DIR / "index.js"

STAR = "⭐"
ROBOT = "🤖"
LINK = "🔗"
BOOK = "📄"
FIRE = "🔥"
CALENDAR = "📅"


def format_message(papers: list[dict], date_str: str = "") -> str:
    """
    Format curated papers into a WhatsApp-ready message.

    Example output:
        🤖 *AI Papers Daily* — 2024-01-15
        ━━━━━━━━━━━━━━━━━━━━━━
        1. 📄 *Some Cool Paper Title*
           ⭐ Score: 9/10
           한국어 요약이 여기에 들어갑니다. 핵심 기여를 설명합니다.
           🔗 https://huggingface.co/papers/xxxx
        ...
    """
    if not date_str:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")

    lines = [
        f"{ROBOT} *AI Curator* — {date_str}",
        "━" * 26,
        f"총 *{len(papers)}개* 항목이 선별되었습니다.\n",
    ]

    for i, paper in enumerate(papers, 1):
        title = paper.get("title", "제목 없음")
        url = paper.get("url", "")
        summary = paper.get("summary_ko", "").strip()
        source = paper.get("source_name", "")
        topics = paper.get("matched_topics", [])

        lines.append(f"{i}. {BOOK} *{title}*")
        topic_str = "  ".join(f"#{t}" for t in topics) if topics else source
        lines.append(f"   {STAR} {topic_str}")
        if summary:
            lines.append(f"   {summary}")
        if url:
            lines.append(f"   {LINK} {url}")
        lines.append("")  # blank line between items

    lines.append("━" * 26)
    lines.append(f"_Powered by Claude API_ {FIRE}")

    return "\n".join(lines)


class WhatsAppSender:
    """Sends messages via the whatsapp-web.js Node.js bridge."""

    def __init__(self, chat_name: str = "", timeout: int = 60):
        self.chat_name = chat_name or os.getenv("WHATSAPP_CHAT_NAME", "AI Papers Daily")
        self.timeout = timeout

    def send(self, message: str) -> bool:
        """
        Spawn the Node bridge and send the message.
        Returns True on success, False on failure.
        """
        if not BRIDGE_SCRIPT.exists():
            logger.error(f"WhatsApp bridge not found at {BRIDGE_SCRIPT}")
            return False

        payload = json.dumps(
            {"chatName": self.chat_name, "message": message},
            ensure_ascii=False,
        )

        logger.info(f"Sending message to WhatsApp chat: '{self.chat_name}'")

        try:
            result = subprocess.run(
                ["node", str(BRIDGE_SCRIPT)],
                input=payload,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                cwd=str(BRIDGE_DIR),
            )

            if result.stdout:
                for line in result.stdout.strip().splitlines():
                    logger.info(f"[bridge] {line}")

            if result.returncode == 0:
                logger.info("WhatsApp message sent successfully.")
                return True
            else:
                logger.error(f"Bridge exited with code {result.returncode}")
                if result.stderr:
                    logger.error(f"[bridge stderr] {result.stderr[:500]}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"WhatsApp bridge timed out after {self.timeout}s.")
            return False
        except FileNotFoundError:
            logger.error("'node' command not found. Please install Node.js.")
            return False
        except Exception as e:
            logger.error(f"Unexpected error sending via WhatsApp bridge: {e}")
            return False

    def send_papers(self, papers: list[dict]) -> bool:
        """Format and send a list of curated papers."""
        if not papers:
            logger.warning("No papers to send.")
            return False
        message = format_message(papers)
        return self.send(message)


def print_to_console(papers: list[dict]):
    """Fallback: print formatted message to stdout (for testing without WhatsApp)."""
    print("\n" + "=" * 60)
    print(format_message(papers))
    print("=" * 60 + "\n")
