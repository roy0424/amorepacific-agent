# 팀원용 가이드 - Laneige Ranking Tracker

> 데이터 분석/모델링 팀원을 위한 빠른 시작 가이드

---

## 🚀 5분 안에 시작하기

### 1단계: 설치 (원클릭)

**Mac/Linux:**
```bash
./setup.sh
```

**Windows:**
```bash
setup.bat
```

설치가 완료되면 다음 단계로 진행하세요!

### 1-1단계: Docker 사용 (선택)

**Docker가 설치되어 있다면 더 쉽게 시작할 수 있습니다:**

```bash
# 모든 서비스 시작 (DB + Prefect + Worker)
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 중지
docker-compose down
```

**장점:**
- 환경 설정 불필요 (Python, PostgreSQL 자동 설치)
- 팀원 간 동일한 환경 보장
- 원클릭으로 전체 시스템 시작

**Prefect UI 접속:** http://localhost:4200

---

## 📊 데이터 수집 방법

### 방법 1: 원클릭 자동 수집 (추천 ⭐)

**단 하나의 명령어로 모든 것이 자동으로 실행됩니다!**

```bash
# Mac/Linux
source .venv/bin/activate
python scripts/start_all.py

# Windows
.venv\Scripts\activate.bat
python scripts\start_all.py
```

**자동으로 실행되는 것들:**
- ✅ Prefect 서버 시작
- ✅ Flow 자동 배포 (스케줄 설정)
- ✅ 1시간마다 Amazon 데이터 자동 수집
- ✅ 6시간마다 소셜미디어 데이터 자동 수집 (설정 시)

**Prefect UI 확인:**
- 브라우저에서 http://localhost:4200 열기
- 실시간으로 데이터 수집 모니터링 가능

**종료:** Ctrl+C

---

### 방법 1-1: 수동 배포 (고급)

서버와 배포를 분리하고 싶다면:

#### 터미널 1: Prefect 서버 시작
```bash
# Mac/Linux
source .venv/bin/activate
python scripts/start_prefect.py

# Windows
.venv\Scripts\activate.bat
python scripts\start_prefect.py
```

#### 터미널 2: Flow 배포 (스케줄링 설정)
```bash
# Mac/Linux
source .venv/bin/activate
python scripts/deploy_flows.py

# Windows
.venv\Scripts\activate.bat
python scripts\deploy_flows.py
```

---

### 방법 2: 수동 수집 (테스트용)

```bash
# Amazon 데이터 수집 (테스트 - 빠름)
python scripts/run_manual.py --flow amazon-test

# Amazon 데이터 수집 (전체)
python scripts/run_manual.py --flow amazon

# 소셜미디어 수집 (TikTok + Instagram)
python scripts/run_social.py
```

---

## 💾 데이터 다운로드 방법

### Excel 파일로 다운로드 (추천)

**모든 데이터를 하나의 Excel 파일로:**
```bash
python scripts/export_data.py --format excel --days 7
```

**생성 파일:**
- `data/exports/amazon_data_YYYYMMDD_HHMMSS.xlsx`
  - 시트 1: Products (제품 목록)
  - 시트 2: Rankings (시계열 랭킹)
  - 시트 3: Brand Summary (브랜드 요약)

- `data/exports/social_media_data_YYYYMMDD_HHMMSS.xlsx`
  - 시트 1: YouTube
  - 시트 2: TikTok
  - 시트 3: Instagram

---

### CSV 파일로 다운로드

**여러 CSV 파일로 분리:**
```bash
python scripts/export_data.py --format csv --days 7
```

**생성 파일:**
- `amazon_products_*.csv` - 제품 정보
- `amazon_rankings_*.csv` - 랭킹 데이터 (시계열)
- `amazon_brand_summary_*.csv` - 브랜드별 요약
- `youtube_data_*.csv` - YouTube 데이터
- `tiktok_data_*.csv` - TikTok 데이터
- `instagram_data_*.csv` - Instagram 데이터

---

### 추출 옵션

```bash
# Amazon 데이터만
python scripts/export_data.py --platform amazon --format excel

# 소셜미디어 데이터만
python scripts/export_data.py --platform social --format excel

# 최근 30일 데이터
python scripts/export_data.py --days 30 --format excel

# 커스텀 출력 경로
python scripts/export_data.py --output-dir /path/to/output --format excel
```

---

## 📁 데이터 구조 이해하기

### Amazon 데이터

**Products (제품)**
- `ASIN`: Amazon 고유 ID
- `Product Name`: 제품명
- `Brand`: 브랜드 (Laneige, Innisfree 등)
- `First Seen`: 최초 수집 시간
- `Last Seen`: 마지막 수집 시간

**Rankings (랭킹 - 시계열)**
- `Collected At`: 수집 시간
- `Category`: 카테고리 (예: Facial Masks)
- `Rank`: 순위 (1-50)
- `Price`: 가격
- `Rating`: 평점
- `Review Count`: 리뷰 수
- `Is Prime`: Prime 여부

---

### 소셜미디어 데이터

**YouTube**
- `Video ID`, `Title`, `Channel`
- `View Count`, `Like Count`, `Comment Count`
- `Published At`, `Collected At`

**TikTok**
- `Video ID`, `Author`, `Description`
- `View Count`, `Like Count`, `Comment Count`, `Share Count`
- `Hashtags`, `Posted At`, `Collected At`

**Instagram**
- `Shortcode`, `Owner`, `Caption`
- `Like Count`, `Comment Count`, `Video View Count`
- `Media Type`, `Hashtags`, `Posted At`, `Collected At`

---

## 🎯 주요 분석 시나리오

### 1. 랭킹 변동 추이 분석
```python
import pandas as pd

# Excel 파일 읽기
df = pd.read_excel('data/exports/amazon_data_*.xlsx', sheet_name='Rankings')

# 라네즈 제품만 필터링
laneige = df[df['Brand'] == 'Laneige']

# 시간에 따른 랭킹 변화
laneige_trend = laneige.groupby('Collected At')['Rank'].mean()
```

### 2. 브랜드별 점유율 분석
```python
# Brand Summary 시트 사용
summary = pd.read_excel('data/exports/amazon_data_*.xlsx', sheet_name='Brand Summary')

# 카테고리별 브랜드 점유율
category_share = summary.groupby('Category')['Product Count'].sum()
```

### 3. 소셜미디어 영향력 분석
```python
# TikTok 데이터
tiktok = pd.read_excel('data/exports/social_media_data_*.xlsx', sheet_name='TikTok')

# 조회수 상위 10개
top_tiktok = tiktok.nlargest(10, 'View Count')

# 해시태그 트렌드 분석
hashtags = tiktok['Hashtags'].str.split(',').explode()
top_hashtags = hashtags.value_counts().head(10)
```

---

## 🗂️ 데이터베이스 직접 접근 (고급)

데이터베이스에 직접 접근하고 싶다면:

```python
from src.core.database import get_db_context
from sqlalchemy import text

with get_db_context() as db:
    # SQL 쿼리 실행
    result = db.execute(text("""
        SELECT
            p.product_name,
            r.rank,
            r.collected_at
        FROM amazon_rankings r
        JOIN amazon_products p ON r.product_id = p.id
        WHERE p.asin = 'B08...'
        ORDER BY r.collected_at DESC
    """))

    for row in result:
        print(row)
```

---

## 🔧 문제 해결

### "가상환경이 활성화되지 않았습니다" 에러

**Mac/Linux:**
```bash
source .venv/bin/activate
```

**Windows:**
```bash
.venv\Scripts\activate.bat
```

### "데이터가 없습니다" 에러

먼저 데이터를 수집하세요:
```bash
python scripts/run_manual.py --flow amazon-test
```

### Prefect UI가 안 열립니다

1. 서버가 실행 중인지 확인
2. 포트 4200이 사용 중인지 확인:
   ```bash
   # Mac/Linux
   lsof -i :4200

   # Windows
   netstat -ano | findstr :4200
   ```

### Excel 파일이 열리지 않습니다

openpyxl 설치 확인:
```bash
pip install openpyxl
```

---

## 📞 도움 요청

데이터 수집 담당자에게 문의:
- 새로운 데이터 소스 추가 요청
- 데이터 포맷 변경 요청
- 수집 주기 변경 요청
- 추가 메트릭 수집 요청

---

## 🎓 추가 리소스

### 상세 문서
- `README.md` - 프로젝트 전체 개요
- `PREFECT_GUIDE.md` - Prefect 사용법 상세 가이드
- `QUICKSTART.md` - 개발자용 빠른 시작 가이드

### Prefect UI 활용
- **Flow Runs**: 모든 실행 내역 확인
- **Logs**: 실시간 로그 확인
- **Deployments**: 스케줄 설정 확인

### 데이터 분석 예제
```python
import pandas as pd
import matplotlib.pyplot as plt

# 랭킹 데이터 로드
df = pd.read_excel('data/exports/amazon_data_*.xlsx', sheet_name='Rankings')

# 라네즈 제품 필터링
laneige = df[df['Brand'] == 'Laneige']

# 시간별 평균 랭킹 시각화
laneige['Collected At'] = pd.to_datetime(laneige['Collected At'])
laneige_trend = laneige.groupby('Collected At')['Rank'].mean()

plt.figure(figsize=(12, 6))
plt.plot(laneige_trend.index, laneige_trend.values)
plt.xlabel('Time')
plt.ylabel('Average Rank')
plt.title('Laneige Products - Average Ranking Over Time')
plt.xticks(rotation=45)
plt.tight_layout()
plt.savefig('laneige_ranking_trend.png')
```

---

## ✅ 체크리스트

설치 및 실행 확인:
- [ ] `setup.sh` 또는 `setup.bat` 실행 완료
- [ ] Prefect 서버 실행 확인 (http://localhost:4200)
- [ ] Flow 배포 완료
- [ ] 데이터 수집 테스트 완료
- [ ] 데이터 추출 테스트 완료
- [ ] Excel/CSV 파일 열기 확인

분석 준비:
- [ ] Pandas 설치 확인
- [ ] Jupyter Notebook 설치 (선택)
- [ ] 데이터 구조 이해 완료
- [ ] 샘플 분석 코드 실행 완료

---

**Happy Analyzing! 📊**