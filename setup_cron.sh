#!/usr/bin/env bash
# setup_cron.sh — .env의 스케줄 설정을 읽어 cron 자동 등록 (Linux/macOS)
#
# 사용법: bash setup_cron.sh
# 제거:   crontab -e 에서 해당 줄 삭제

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/.env"

# ── .env 읽기 ─────────────────────────────────────────────────────────────────
if [ ! -f "$ENV_FILE" ]; then
  echo "❌ .env 파일이 없습니다. 먼저 install.sh를 실행하세요."
  exit 1
fi

# .env에서 값 추출 (주석, 공백 무시)
get_env() {
  grep -E "^${1}=" "$ENV_FILE" | head -1 | cut -d'=' -f2- | tr -d '"' | tr -d "'"
}

SCHEDULE_TIME="$(get_env SCHEDULE_TIME)"
SCHEDULE_DAYS="$(get_env SCHEDULE_DAYS)"

# 기본값
SCHEDULE_TIME="${SCHEDULE_TIME:-08:00}"
SCHEDULE_DAYS="${SCHEDULE_DAYS:-mon,tue,wed,thu,fri}"

# ── 시간 파싱 ─────────────────────────────────────────────────────────────────
HOUR=$(echo "$SCHEDULE_TIME" | cut -d':' -f1 | sed 's/^0//')
MINUTE=$(echo "$SCHEDULE_TIME" | cut -d':' -f2 | sed 's/^0//')
HOUR="${HOUR:-8}"
MINUTE="${MINUTE:-0}"

# ── 요일 파싱 (mon→1, tue→2, ... sun→0) ──────────────────────────────────────
day_to_num() {
  case "$(echo "$1" | tr '[:upper:]' '[:lower:]')" in
    sun|sunday)    echo "0" ;;
    mon|monday)    echo "1" ;;
    tue|tuesday)   echo "2" ;;
    wed|wednesday) echo "3" ;;
    thu|thursday)  echo "4" ;;
    fri|friday)    echo "5" ;;
    sat|saturday)  echo "6" ;;
    *) echo ""; echo "⚠️  알 수 없는 요일: $1" >&2 ;;
  esac
}

DAY_NUMS=""
IFS=',' read -ra DAYS <<< "$SCHEDULE_DAYS"
for day in "${DAYS[@]}"; do
  day=$(echo "$day" | tr -d ' ')
  num=$(day_to_num "$day")
  [ -n "$num" ] && DAY_NUMS="${DAY_NUMS:+$DAY_NUMS,}$num"
done

# 전체 요일이면 * 로 단순화
if [ "$DAY_NUMS" = "0,1,2,3,4,5,6" ] || [ "$DAY_NUMS" = "1,2,3,4,5,6,0" ]; then
  DAY_NUMS="*"
fi

# ── cron 표현식 생성 ──────────────────────────────────────────────────────────
CRON_EXPR="$MINUTE $HOUR * * $DAY_NUMS"
PYTHON="$SCRIPT_DIR/venv/bin/python3"
CRON_LOG="$SCRIPT_DIR/cron.log"
CRON_LINE="$CRON_EXPR cd $SCRIPT_DIR && $PYTHON run.py >> $CRON_LOG 2>&1"

# ── crontab 등록 (중복 방지) ──────────────────────────────────────────────────
(crontab -l 2>/dev/null | grep -v "ai-curator/run.py"; echo "$CRON_LINE") | crontab -

echo ""
echo "✅ Cron 등록 완료"
echo "   스케줄 : $SCHEDULE_TIME, 요일: $SCHEDULE_DAYS"
echo "   Cron   : $CRON_EXPR"
echo "   로그   : $CRON_LOG"
echo ""
echo "확인: crontab -l"
echo "제거: crontab -e  (해당 줄 삭제)"
