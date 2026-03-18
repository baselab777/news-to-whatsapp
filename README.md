# 🤖 AI Curator

Claude가 매일 관심 토픽을 검색해서 논문/뉴스를 WhatsApp으로 보내줍니다.

## 동작 방식

```
Claude (web_search 툴로 검색 + 한국어 요약)
  → 이미 보낸 것 제외
  → WhatsApp 전송
  → 전송 이력 저장
```

스크래퍼 없음. Claude가 직접 검색합니다.

---

## 설치

```bash
bash install.sh
```

venv 생성, Python/Node 패키지 설치, `.env` 생성까지 한 번에.

---

## 설정 (`.env`)

```env
ANTHROPIC_API_KEY=sk-ant-...          # Claude API 키
WHATSAPP_CHAT_NAME=AI Papers Daily    # 전송할 채팅방 이름
TOPICS=LLM, multimodal, AI agent      # 관심 토픽

MAX_SEND=1                            # 하루 최대 전송 개수
SCHEDULE_TIME=08:00                   # 실행 시각
SCHEDULE_DAYS=mon,tue,wed,thu,fri     # 실행 요일
```

---

## WhatsApp 인증 (최초 1회)

```bash
bash auth_whatsapp.sh
```

QR 코드 → WhatsApp 앱 → 설정 → 연결된 기기 → 기기 연결 → 스캔.

---

## 실행

```bash
source venv/bin/activate
python run.py             # 전체 실행
python run.py --dry-run   # 전송 없이 터미널 출력 (테스트)
```

---

## 자동 실행

```bash
bash setup_cron.sh   # .env 읽어서 cron 등록
```

---

## 커스터마이징

| 목적 | 방법 |
|------|------|
| 토픽 변경 | `.env`의 `TOPICS` 수정 |
| 검색 기준 세밀하게 | `SKILL.md` 편집 (있으면 TOPICS 무시됨) |
| 전송 개수 조정 | `.env`의 `MAX_SEND` 수정 |
