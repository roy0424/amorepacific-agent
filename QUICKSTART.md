# 빠른 시작 가이드 (Prefect 기반)

이 가이드는 아마존 크롤링 파이프라인을 빠르게 테스트하고 실행하는 방법을 안내합니다.

## 1단계: 환경 설정

### 가상환경 및 의존성 설치

```bash
# 가상환경 생성
python -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# 또는
venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# Playwright 브라우저 설치
playwright install chromium
```

### 환경 변수 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집 (필수 항목만)
# DATABASE_URL은 Postgres 사용
# OPENAI_API_KEY는 Phase 3에서 필요 (지금은 생략 가능)
```

## 2단계: 데이터베이스 초기화

```bash
# DB 테이블 생성 및 초기 데이터 시딩
python scripts/init_db.py
```

**예상 출력:**
```
[INFO] Initializing database...
[INFO] Creating all tables...
[INFO] Seeding brands...
[INFO] - Created brand: Laneige (target)
[INFO] - Created brand: Vaseline (competitor)
[INFO] Seeding categories...
[INFO] - Created category: Beauty & Personal Care
[INFO] Database initialization complete!
```

## 3단계: 크롤러 테스트 (중요!)

프로덕션 실행 전에 먼저 테스트를 실행하세요.

### 옵션 A: 빠른 테스트 (권장)

```bash
# 한 개 카테고리에서 10개 제품만 크롤링 (약 1-2분 소요)
python scripts/run_manual.py --flow amazon-test
```

**예상 출력:**
```
[INFO] Running Amazon quick test...
[INFO] Task: Scraping Amazon category - Beauty & Personal Care
[INFO] Starting Amazon scraper...
[INFO] Browser started with UA: Mozilla/5.0...
[INFO] Scraping category: Beauty & Personal Care
[INFO] Scraped 10 products from Beauty & Personal Care
[INFO] Test complete: Scraped 10 products

  1. [1] e.l.f. Halo Glow Liquid Filter...
     ASIN: B09Q5F7K8K, Price: $14.0
  2. [2] Neutrogena Makeup Remover Cleansing...
     ASIN: B01M4MCUAF, Price: $8.97
```

### 옵션 B: 전체 파이프라인 테스트

```bash
# 5개 카테고리 전체 크롤링 (약 5-10분 소요)
python scripts/run_manual.py --flow amazon
```

**예상 출력:**
```
[INFO] ================================================================================
[INFO] Starting Amazon Scraping Pipeline
[INFO] ================================================================================
[INFO] Step 1/4: Scraping Amazon categories...
[INFO] Scraping category: Beauty & Personal Care
[INFO] Scraped 50 products from Beauty & Personal Care
[INFO] Scraping category: Lip Care Products
[INFO] Scraped 50 products from Lip Care Products
...
[INFO] Step 2/4: Validating data quality...
[INFO] Validation complete: 245/250 valid products
[INFO] Step 3/4: Saving to database...
[INFO] Database save complete: 250 rankings created
[INFO] Step 4/4: Creating backup...
[INFO] Backup complete: data/backups/amazon_backup_20250117_143022.json
[INFO] ================================================================================
[INFO] Amazon Pipeline Complete - Duration: 487.3s
[INFO] ================================================================================
```

### 문제 해결

**CAPTCHA 감지 시:**
```
[WARNING] CAPTCHA detected - manual intervention required
```
→ 해결: `config/settings.py`에서 `PLAYWRIGHT_HEADLESS = False`로 변경하고 재실행

**봇 차단 시:**
```
[WARNING] Block detected: To discuss automated access...
```
→ 해결: 몇 분 기다렸다가 재실행, 또는 User-Agent 로테이션 확인

## 4단계: Prefect 서버 & 자동 실행

### 터미널 1: Prefect UI 서버 시작

```bash
python scripts/start_prefect.py
# 또는
prefect server start
```

브라우저에서 http://localhost:4200 열기

### 터미널 2: Flows 배포 (자동 스케줄링)

```bash
python scripts/deploy_flows.py
```

**예상 출력:**
```
[INFO] ================================================================================
[INFO] Deploying Prefect Flows
[INFO] ================================================================================
[INFO] Deploying Amazon pipeline (every 1 hours)...
[INFO] All flows deployed successfully!
[INFO] Prefect will now run the flows according to their schedules.
[INFO] View dashboard at: http://localhost:4200
```

이제 파이프라인이 1시간마다 자동으로 실행됩니다!

## 5단계: Prefect UI에서 모니터링

### 대시보드 메뉴

1. **Flow Runs** - 실행 히스토리
   - 각 실행의 성공/실패 상태 확인
   - 실행 시간 및 로그 확인

2. **Flows** - 등록된 Flow 목록
   - `amazon-scraping-pipeline` 확인

3. **Deployments** - 배포된 스케줄
   - `amazon-hourly` 확인
   - 수동 실행 버튼 (Quick Run)

4. **Logs** - 실시간 로그
   - 크롤링 진행 상황 실시간 확인

### Flow Run 상세 페이지

- **Task 실행 그래프**: 각 Task의 의존성 시각화
- **로그 탭**: 전체 실행 로그
- **Artifacts**: 실행 결과 데이터

## 데이터 확인

### 데이터베이스 조회 (Postgres)

```bash
# Postgres 접속
psql "postgresql+psycopg://laneige:laneige@localhost:5432/laneige_tracker"

# 수집된 제품 수 확인
laneige_tracker=> SELECT COUNT(*) FROM amazon_products;

# 라네즈 제품만 확인
laneige_tracker=> SELECT p.product_name, r.rank, r.price
        FROM amazon_products p
        JOIN amazon_rankings r ON p.id = r.product_id
        WHERE p.product_name LIKE '%laneige%'
        ORDER BY r.collected_at DESC
        LIMIT 10;

# 종료
laneige_tracker=> \\q
```

### JSON 백업 확인

```bash
# 백업 파일 목록
ls -lh data/backups/

# 최신 백업 파일 확인
cat data/backups/amazon_backup_*.json | head -50
```

## 다음 단계

Phase 1 완료! 이제 다음을 진행할 수 있습니다:

- ✅ **Phase 2**: 소셜미디어 크롤링 (TikTok, YouTube, Instagram)
- ✅ **Phase 3**: AI 인사이트 생성 (GPT-4)
- ✅ **Phase 4**: 엑셀 리포트 생성

## 명령어 치트시트

```bash
# 데이터베이스 초기화
python scripts/init_db.py

# 크롤러 테스트 (10개 제품)
python scripts/run_manual.py --flow amazon-test

# 전체 파이프라인 수동 실행
python scripts/run_manual.py --flow amazon

# Prefect 서버 시작
python scripts/start_prefect.py

# Flows 배포 (새 터미널)
python scripts/deploy_flows.py

# Prefect UI 접속
# http://localhost:4200
```

## 문제 발생 시

### 로그 확인

```bash
# 최신 로그 파일 확인
tail -f data/logs/app_*.log

# 에러 로그만 확인
tail -f data/logs/error_*.log
```

### 일반적인 문제

1. **ModuleNotFoundError**
   ```bash
   # PYTHONPATH 설정
   export PYTHONPATH="${PYTHONPATH}:$(pwd)"
   ```

2. **Playwright 브라우저 없음**
   ```bash
   playwright install chromium
   ```

3. **데이터베이스 연결**
   - Postgres 접속 정보 확인

4. **봇 차단 지속**
   - `SCRAPING_DELAY_MIN`, `SCRAPING_DELAY_MAX` 값 증가
   - `PLAYWRIGHT_HEADLESS = False`로 변경하여 수동 CAPTCHA 해결

## 성공 확인 체크리스트

- [ ] `scripts/init_db.py` 실행 성공
- [ ] `python scripts/run_manual.py --flow amazon-test` 실행 성공
- [ ] 10개 제품 정보 출력 확인
- [ ] Postgres에 테이블 생성 확인
- [ ] `data/backups/` 폴더에 JSON 파일 생성 확인
- [ ] Prefect UI (http://localhost:4200) 접속 확인
- [ ] Flow Runs 페이지에서 실행 히스토리 확인

모든 체크리스트가 완료되면 Phase 1 성공입니다! 🎉
