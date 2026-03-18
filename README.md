# 🤖 AI Curator

AI 논문/뉴스를 매일 자동 수집 → Claude로 필터링 → WhatsApp 전송.

## 설치 (한 번만)

```bash
bash install.sh          # venv 생성 + Python/Node 패키지 설치
# .env 파일 열어서 ANTHROPIC_API_KEY, WHATSAPP_CHAT_NAME 입력
bash auth_whatsapp.sh    # WhatsApp QR 인증 (최초 1회)
```

## 실행

```bash
source venv/bin/activate

python run.py                    # 오늘 날짜, 전체 실행
python run.py --dry-run          # WhatsApp 전송 없이 터미널 출력
python run.py --date 2025-01-15  # 특정 날짜 지정
python run.py --scrape-only      # 스크래핑 결과만 확인
```

## 스케줄 설정

`.env`에서 시간과 요일을 설정하고 `setup_cron.sh`을 실행하면 끝:

```env
SCHEDULE_TIME=08:00                      # 실행 시각 (24시간제)
SCHEDULE_DAYS=mon,tue,wed,thu,fri        # 실행 요일 (쉼표 구분)
```

요일 예시: `mon,wed,fri` / `mon,tue,wed,thu,fri,sat,sun` (매일) / `sat,sun` (주말만)

```bash
bash setup_cron.sh   # .env 읽어서 cron 자동 등록
```

> **Windows** — 작업 스케줄러(taskschd.msc) → 작업 만들기 → 트리거에서 원하는 요일/시간 선택
> 동작: `C:\...\venv\Scripts\python.exe`, 인수: `run.py`, 시작위치: 프로젝트 폴더

## 소스 추가하기

`sources/` 폴더에 파일 하나 추가하면 됩니다:

```python
# sources/techcrunch.py
from sources.base import ContentSource

class TechCrunchSource(ContentSource):
    name = "TechCrunch"
    content_type = "news"   # "paper" | "news" | "blog" | ...

    def scrape(self) -> list[dict]:
        # 스크래핑 후 반환
        return [{"title": "...", "url": "...", "abstract": "...",
                 "source_name": self.name, "date": "2024-01-15"}]
```

그 다음 `sources/registry.py`에 한 줄 추가:

```python
ACTIVE_SOURCES = [
    HuggingFaceSource(max_items=20),
    TechCrunchSource(),          # ← 추가
]
```

## 관심 토픽 설정

`.env`에서 키워드를 넣으면 Claude가 그것과 관련된 것만 선별합니다:

```env
TOPICS=LLM, multimodal, AI agent, reasoning, efficient inference
```

더 세밀하게 제어하고 싶으면 `SKILL.md`를 직접 편집하세요.
`SKILL.md`가 있으면 TOPICS 대신 그게 우선 적용됩니다.

---

### Windows 작업 스케줄러

1. 작업 스케줄러(taskschd.msc) → 작업 만들기
2. 트리거: 매일 오전 8:00
3. 동작 → 프로그램: `C:\...\venv\Scripts\python.exe`, 인수: `run.py`, 시작위치: 프로젝트 폴더
