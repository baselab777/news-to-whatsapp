"""
run.py — AI Curator 실행

사용법:
    python run.py               # 전체 실행
    python run.py --dry-run     # 전송 없이 터미널 출력
    python run.py --debug       # 디버그 로그
"""

import argparse
import logging
import os
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("curator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run")


def run_pipeline(dry_run: bool = False):
    logger.info("=== AI Curator 시작 ===")

    # 1. 에이전트 검색 + 요약
    import agent
    max_send = int(os.getenv("MAX_SEND", "1"))
    items = agent.run(max_items=max_send * 3)  # 여유있게 가져와서 dedup 후 자름

    if not items:
        logger.info("결과 없음.")
        return

    # 2. 중복 제거
    from dedup import DedupLog
    dedup = DedupLog(log_path=os.getenv("DEDUP_LOG_PATH", "./sent_log.json"))
    dedup.cleanup()
    items = dedup.filter_new(items)

    if not items:
        logger.info("모두 이미 전송된 항목입니다.")
        return

    # 3. 개수 제한
    items = items[:max_send]

    # 4. 전송
    if dry_run:
        from sender import print_to_console
        print_to_console(items)
    else:
        from sender import WhatsAppSender
        sender = WhatsAppSender(chat_name=os.getenv("WHATSAPP_CHAT_NAME", "AI Papers Daily"))
        if not sender.send_papers(items):
            logger.error("전송 실패")
            sys.exit(1)

    # 5. 이력 저장
    dedup.mark_sent_batch(items)
    logger.info(f"=== 완료 — {len(items)}개 전송 ===")


def main():
    parser = argparse.ArgumentParser(description="AI Curator")
    parser.add_argument("--dry-run", action="store_true", help="터미널 출력만 (전송 없음)")
    parser.add_argument("--debug", action="store_true", help="디버그 로그")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    run_pipeline(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
