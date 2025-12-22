# TikTok US Market Collection Guide 🇺🇸

**미국 시장 타겟 TikTok 데이터 수집 가이드**

## 📋 목차

1. [수집 전략 개요](#수집-전략-개요)
2. [수집 기준](#수집-기준)
3. [사용 방법](#사용-방법)
4. [예산 관리](#예산-관리)
5. [데이터 분석](#데이터-분석)

---

## 🎯 수집 전략 개요

### 타겟 시장
- **지역**: 미국 (United States)
- **언어**: 영어 (English)
- **시간대**: EST (Eastern Standard Time)

### 핵심 전략
1. **브랜드 모니터링**: `#laneige`, `#laneigeusa`
2. **제품별 추적**: Lip Sleeping Mask (미국 베스트셀러)
3. **인플루언서 분석**: 미국 뷰티 인플루언서
4. **트렌드 파악**: K-Beauty 카테고리

---

## 📊 수집 기준

### 1️⃣ 브랜드 해시태그 (우선순위: 높음)

```python
#laneige
#laneigeusa
#laneigebeauty
```

### 2️⃣ 제품별 해시태그 (우선순위: 높음)

#### Lip Sleeping Mask (미국 1위 제품)
```python
#laneigelipsleepingmask
#lipsleepingmask
#laneigelipmask
#laneigegummybear    # 인기 향
#laneigeberry        # 인기 향
```

#### 기타 주요 제품
```python
#laneigewatersleepingmask
#laneigecreamskin
#laneigecushion
#laneigewaterbank
```

### 3️⃣ 카테고리 해시태그 (우선순위: 중간)

```python
#kbeauty
#koreanbeauty
#koreanskincare
#skincare
#lipcare
#sleepingmask
```

### 4️⃣ 인플루언서 계정 (우선순위: 높음)

**공식 계정**
- `@laneige_us` (라네즈 미국 공식)
- `@sephora` (주요 유통사)
- `@target` (타겟 스토어)

**미국 뷰티 인플루언서**
- `@jamescharles` (4천만 팔로워)
- `@nikkietutorials` (1천만 팔로워)
- `@hyram` (스킨케어 전문)
- `@jackieaina` (뷰티 구루)

### 5️⃣ 필터 기준

#### 일일 수집 (매일)
- **좋아요**: 1,000개 이상 (바이럴 콘텐츠만)
- **날짜**: 최근 1일
- **비디오 수**: 해시태그당 50개

#### 주간 수집 (주 1회)
- **좋아요**: 500개 이상 (인기 콘텐츠)
- **날짜**: 최근 7일
- **비디오 수**: 해시태그당 100개

#### 월간 수집 (월 1회)
- **좋아요**: 5,000개 이상 (메가 바이럴만)
- **날짜**: 최근 30일
- **비디오 수**: 해시태그당 200개

---

## 🚀 사용 방법

### 기본 사용법

#### 1. 일일 수집 (추천)
```bash
python scripts/run_tiktok_us_collection.py --mode daily
```

**수집 내용**:
- `#laneige`, `#laneigeusa`
- `#laneigelipsleepingmask`
- `#laneigecreamskin`
- 좋아요 1,000개 이상
- 최근 1일 데이터

**예상 소요**: 약 35개 비디오 (무료 크레딧 범위)

---

#### 2. 주간 수집
```bash
python scripts/run_tiktok_us_collection.py --mode weekly
```

**수집 내용**:
- 모든 제품 해시태그
- K-Beauty 카테고리
- 좋아요 500개 이상
- 최근 7일 데이터

**예상 소요**: 약 250개 비디오

---

#### 3. 인플루언서 모니터링
```bash
python scripts/run_tiktok_us_collection.py --mode influencer
```

**수집 내용**:
- 공식 계정 최신 영상
- 주요 인플루언서 영상
- 제한 없음 (모든 콘텐츠)

---

#### 4. 키워드 검색
```bash
python scripts/run_tiktok_us_collection.py --mode keyword
```

**검색 키워드**:
- "laneige lip sleeping mask"
- "laneige water sleeping mask"
- "best korean lip mask"
- "laneige vs drunk elephant"
- etc.

---

#### 5. 전체 수집 (비용 주의!)
```bash
python scripts/run_tiktok_us_collection.py --mode all
```

⚠️ **경고**: 무료 크레딧($5) 모두 사용할 수 있음!

---

### 고급 옵션

#### Dry Run (미리보기)
실제 수집하지 않고 무엇을 수집할지 확인:
```bash
python scripts/run_tiktok_us_collection.py --mode daily --dry-run
```

---

## 💰 예산 관리

### 무료 크레딧 활용

**매월 무료**: $5 (약 1,000개 비디오)

#### 권장 배분
- **일일 수집** (30일): 35개/일 × 30일 = **1,050개**
  - 비용: 약 **$5.25** ❌ (초과!)

**최적 전략**:
```python
# 옵션 1: 격일 수집
- 일일 수집: 2일마다 (월 15회)
- 비용: 35개 × 15회 = 525개 = $2.60 ✅

# 옵션 2: 주간 + 월간
- 주간 수집: 주 1회 (월 4회) = 250개 × 4 = 1,000개
- 비용: $5.00 ✅

# 옵션 3: 혼합 (추천)
- 일일 (중요 해시태그만): 20개/일 × 30일 = 600개
- 주간 (상세 분석): 주 1회 = 100개
- 월간 (트렌드): 월 1회 = 200개
- 합계: 900개 = $4.50 ✅
```

### 비용 모니터링

스크립트가 자동으로 비용 예상:
```
Cost Estimation:
  - Total videos: 100
  - Estimated cost: $0.50
  - Monthly budget: $5.00
  - Remaining budget: $4.50
```

---

## 📊 데이터 분석

### 수집된 데이터 구조

```json
{
  "video_id": "7123456789012345678",
  "video_url": "https://www.tiktok.com/@user/video/7123456789012345678",
  "author_username": "beautyinfluencer",
  "description": "Obsessed with @laneige lip sleeping mask! 💙 #laneige #kbeauty",
  "hashtags": "laneige,kbeauty,skincare",
  "view_count": 1234567,
  "like_count": 123456,
  "comment_count": 1234,
  "share_count": 567,
  "published_at": "2025-12-18T12:00:00"
}
```

### 분석 지표

#### 1. 브랜드 인지도
- 총 조회수 합계
- 해시태그 사용 빈도
- 일별 언급량 추이

#### 2. 제품 인기도
- 제품별 언급 횟수
- Engagement Rate = (좋아요 + 댓글 + 공유) / 조회수
- 바이럴 콘텐츠 비율

#### 3. 인플루언서 영향력
- Top 인플루언서 식별
- 영향력 점수 계산
- ROI 분석

#### 4. 경쟁사 비교
- 브랜드별 언급량
- 카테고리 점유율
- 트렌드 변화

---

## 🔄 자동화 스케줄

### Cron 설정 (Linux/Mac)

```bash
# 매일 오전 9시 (EST) 실행
0 9 * * * cd /path/to/project && python scripts/run_tiktok_us_collection.py --mode daily

# 매주 월요일 오전 10시 실행
0 10 * * 1 cd /path/to/project && python scripts/run_tiktok_us_collection.py --mode weekly

# 매월 1일 오전 11시 실행
0 11 1 * * cd /path/to/project && python scripts/run_tiktok_us_collection.py --mode monthly
```

### Prefect Scheduler (추천)

```python
from prefect import flow, task
from prefect.schedules import CronSchedule

@flow(schedule=CronSchedule(cron="0 9 * * *"))  # 매일 오전 9시
def daily_tiktok_collection():
    # 수집 로직
    pass
```

---

## 🎯 수집 우선순위 요약

| 모드 | 빈도 | 비디오 수 | 비용 | 우선순위 |
|------|------|----------|------|----------|
| **일일** | 매일 | 35개 | $0.17/일 | ⭐⭐⭐⭐⭐ |
| **주간** | 주 1회 | 250개 | $1.25/주 | ⭐⭐⭐⭐ |
| **월간** | 월 1회 | 200개 | $1.00/월 | ⭐⭐⭐ |
| **인플루언서** | 주 1회 | 50개 | $0.25/주 | ⭐⭐⭐⭐ |
| **키워드** | 월 2회 | 100개 | $0.50/월 | ⭐⭐⭐ |

---

## 📌 핵심 포인트

### ✅ DO
1. **일일 수집**을 메인으로 사용 (트렌드 파악)
2. **좋아요 필터**로 퀄리티 유지
3. **무료 크레딧** 범위 내에서 운영
4. **인플루언서 모니터링** 병행

### ❌ DON'T
1. `--mode all` 무분별 사용 (예산 초과)
2. 필터 없이 전체 수집 (노이즈 많음)
3. 경쟁사에 과도한 리소스 투입
4. 한글 해시태그 사용 (미국 시장 아님)

---

## 🆘 트러블슈팅

### Q: 수집되는 비디오가 너무 적어요
**A**: 필터 기준을 낮춰보세요
```python
min_likes = 100  # 1000 → 100으로 낮춤
```

### Q: 무료 크레딧을 초과했어요
**A**: 일일 수집 횟수를 줄이거나 격일로 실행하세요

### Q: 특정 인플루언서를 추가하고 싶어요
**A**: `config/tiktok_strategy_us.py`의 `US_INFLUENCERS` 리스트에 추가

---

## 📚 관련 문서

- [Apify 설정 가이드](APIFY_SETUP_GUIDE.md)
- [TikTok 전략 설정](config/tiktok_strategy_us.py)
- [메인 README](README.md)

---

**Happy Collecting! 🚀**
