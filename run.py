"""
run.py — AI Curator 메인 실행 파일

사용법:
    python run.py                        # 오늘 날짜, 전체 파이프라인
    python run.py --dry-run              # WhatsApp 전송 없이 터미널 출력
    python run.py --date 2025-01-15      # 특정 날짜 지정 (dedup 기준일)
    python run.py --scrape-only          # 스크래핑 결과만 출력
    python run.py --no-whatsapp          # Claude 필터링까지, 전송 없이 출력
    python run.py --debug                # 디버그 로그 활성화
"""

import argparse
import logging
import os
import sys
from datetime import datetime, date
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("curator.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("run")


def parse_date(date_str: str) -> str:
    """Validate and normalise a YYYY-MM-DD string."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
        return d.isoformat()
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"날짜 형식이 잘못됐습니다: '{date_str}' (올바른 형식: YYYY-MM-DD)"
        )


def run_pipeline(
    target_date: str,
    dry_run: bool = False,
    scrape_only: bool = False,
    no_whatsapp: bool = False,
):
    logger.info(f"=== AI Curator 시작 — {target_date} ===")

    # ── 1. Scrape ─────────────────────────────────────────────────────────────
    from sources.registry import ACTIVE_SOURCES

    all_items: list[dict] = []
    for source in ACTIVE_SOURCES:
        try:
            items = source.scrape()
            logger.info(f"[{source.name}] → {len(items)}개 수집")
            all_items.extend(items)
        except Exception as e:
            logger.error(f"[{source.name}] 스크래핑 실패: {e}")

    logger.info(f"총 수집: {len(all_items)}개 ({len(ACTIVE_SOURCES)}개 소스)")

    if not all_items:
        logger.warning("수집된 항목이 없습니다. 종료.")
        return

    if scrape_only:
        print(f"\n{'─'*60}")
        for item in all_items:
            ctype = item.get("content_type", "?")
            print(f"  [{ctype}] {item.get('title', '제목 없음')}")
            print(f"         {item.get('url', '')}")
        print(f"{'─'*60}\n")
        return

    # ── 2. Dedup (Claude 호출 전 — API 비용 절약) ─────────────────────────────
    from dedup import DedupLog
    dedup = DedupLog(log_path=os.getenv("DEDUP_LOG_PATH", "./sent_log.json"))
    dedup.cleanup()

    new_items = dedup.filter_new(all_items)
    logger.info(f"중복 제거 후: {len(new_items)}개 새 항목")

    if not new_items:
        logger.info("오늘 새로운 항목이 없습니다.")
        return

    # ── 3. Claude 큐레이션 ────────────────────────────────────────────────────
    from curator import curate, load_topics
    topics = load_topics()
    if topics:
        logger.info(f"토픽 필터: {topics}")
    curated = curate(
        papers=new_items,
        topics=topics,
        skill_path=os.getenv("SKILL_FILE_PATH", "./SKILL.md"),
    )
    logger.info(f"큐레이션 완료: {len(curated)}개 선별")

    if not curated:
        logger.info("선별된 항목이 없습니다.")
        return

    # ── MAX_SEND 제한 ─────────────────────────────────────────────────────────
    max_send = int(os.getenv("MAX_SEND", "1"))
    if len(curated) > max_send:
        logger.info(f"상위 {max_send}개만 전송 (전체 {len(curated)}개 중)")
        curated = curated[:max_send]

    # ── 4. 전송 ───────────────────────────────────────────────────────────────
    if dry_run or no_whatsapp:
        from sender import print_to_console
        print_to_console(curated)
    else:
        from sender import WhatsAppSender
        sender = WhatsAppSender(chat_name=os.getenv("WHATSAPP_CHAT_NAME", "AI Papers Daily"))
        success = sender.send_papers(curated)
        if not success:
            logger.error("WhatsApp 전송 실패 — 전송 이력 기록 안 됨.")
            sys.exit(1)

    # ── 5. 전송 이력 저장 ─────────────────────────────────────────────────────
    dedup.mark_sent_batch(curated)
    logger.info(f"=== 완료 — {len(curated)}개 전송 ===")


def main():
    parser = argparse.ArgumentParser(description="AI Paper/News Curator")
    parser.add_argument(
        "--date",
        type=parse_date,
        default=date.today().isoformat(),
        metavar="YYYY-MM-DD",
        help="처리 날짜 (기본값: 오늘)",
    )
    parser.add_argument("--dry-run", action="store_true", help="터미널 출력만, 전송 없음")
    parser.add_argument("--scrape-only", action="store_true", help="스크래핑 결과만 확인")
    parser.add_argument("--no-whatsapp", action="store_true", help="Claude 필터링까지, 전송 없음")
    parser.add_argument("--debug", action="store_true", help="디버그 로그 활성화")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    run_pipeline(
        target_date=args.date,
        dry_run=args.dry_run,
        scrape_only=args.scrape_only,
        no_whatsapp=args.no_whatsapp,
    )


if __name__ == "__main__":
    main()
