# Laneige Ranking Tracker & Analysis Agent

아마존과 소셜미디어에서 라네즈 제품 데이터를 자동 수집하고 AI 기반 인사이트를 생성하는 에이전트 시스템

## 주요 기능

- 🛒 **아마존 랭킹 자동 수집** (1시간 주기, 5개 카테고리)
- 📱 **소셜미디어 바이럴 데이터 수집** (TikTok, YouTube, Instagram - 6시간 주기)
- 🏆 **전체 제품 랭킹 저장** (라네즈 + 경쟁사 포함)
- 🤖 **AI 기반 인사이트 자동 생성** (GPT-4)
- 📊 **엑셀 리포트 출력** (일자별/카테고리별)
- 🔔 **실시간 알림** (급등/급락 감지 - Phase 4)

## 기술 스택

- **언어**: Python 3.11+
- **워크플로우**: Prefect OSS 2.0 (무료!) 🚀
- **크롤링**: Playwright
- **데이터베이스**: SQLAlchemy + PostgreSQL/SQLite
- **AI/LLM**: OpenAI GPT-4 + LangChain
- **리포트**: openpyxl + Plotly
- **로깅**: Loguru + Prefect Logging

## 빠른 시작

### 1. 환경 설정

```bash
# 가상환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키 등을 설정하세요
```

### 2. 데이터베이스 초기화

```bash
python scripts/init_db.py
```

### 3. Prefect 서버 & Flows 실행

```bash
# 터미널 1: Prefect UI 서버 시작
prefect server start
# → http://localhost:4200 에서 대시보드 확인!

# 터미널 2: Flows 배포 (자동 실행 시작)
python scripts/deploy_flows.py

# 수동 실행 (테스트)
python scripts/run_manual.py --flow amazon
```

## 프로젝트 구조

```
laneige-ranking-tracker/
├── config/              # 설정 파일
├── src/
│   ├── core/           # 핵심 인프라 (DB, 로깅)
│   ├── models/         # 데이터베이스 모델
│   ├── scrapers/       # 크롤러 (Amazon, TikTok, YouTube, Instagram)
│   ├── services/       # 비즈니스 로직
│   ├── analyzers/      # 데이터 분석
│   ├── insights/       # AI 인사이트 생성
│   └── reports/        # 리포트 생성
├── scripts/            # 실행 스크립트
├── data/               # 데이터 저장소
│   ├── backups/       # JSON 백업
│   ├── reports/       # 엑셀 리포트
│   └── logs/          # 로그 파일
└── tests/              # 테스트
```

## 개발 단계

- ✅ **Phase 1**: MVP (아마존 크롤링 + 기본 리포트)
- ⏳ **Phase 2**: 소셜미디어 통합
- 📅 **Phase 3**: AI 인사이트 생성
- 📅 **Phase 4**: 대시보드 & 실시간 알림

## 환경 변수 설정

`.env` 파일에서 다음 변수를 설정해야 합니다:

```bash
# 필수
DATABASE_URL=sqlite:///data/laneige_tracker.db
OPENAI_API_KEY=sk-your-key-here
YOUTUBE_API_KEY=AIzaSy-your-key-here

# 선택
PLAYWRIGHT_HEADLESS=true
AMAZON_SCRAPE_INTERVAL_HOURS=1
SOCIAL_SCRAPE_INTERVAL_HOURS=6
```

## 문서

자세한 구현 계획은 [PLAN.md](./PLAN.md)를 참조하세요.

## 라이선스

Private Project

## 기여

공모전 프로젝트입니다.
