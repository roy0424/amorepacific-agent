# Oxylabs TikTok Scraper 사용 가이드

## 📌 개요

**Oxylabs TikTok Scraper API**는 승인 없이 바로 사용 가능한 상업용 TikTok 데이터 수집 서비스입니다.

TikTok Research API와 달리 **누구나 가입 후 바로 사용** 가능하며, 안정적이고 강력한 데이터 수집을 제공합니다.

## ✅ 장점

| 항목 | Oxylabs | TikTok Research API | Playwright |
|------|---------|---------------------|------------|
| **가입/승인** | ✅ 즉시 가입 | ❌ 연구자만, 승인 필요 | ✅ 불필요 |
| **안정성** | ✅ 매우 안정적 | ✅ 안정적 | ❌ 불안정 (차단) |
| **상업적 사용** | ✅ 가능 | ❌ 불가 | ⚠️ 그레이존 |
| **Headless 지원** | ✅ 완벽 지원 | ✅ 지원 | ❌ 차단됨 |
| **설정 난이도** | ✅ 매우 쉬움 | ⚠️ 복잡 | ⚠️ 보통 |
| **비용** | 💰 유료 | ✅ 무료 | ✅ 무료 |

## 💰 가격

- **무료 평가판**: 7일 무료 체험
- **Micro**: $49/월 - 24,500 요청 ($2/1K)
- **Starter**: $149/월 - 100,000 요청 ($1.49/1K)
- **Advanced**: $499/월 - 500,000 요청 ($1/1K)
- **Enterprise**: $10,000+/월 - 커스텀

💡 **TikTok 크롤링 비용 예상:**
- 하루 100개 비디오 수집 = 100 요청/일 = 3,000 요청/월
- **Micro 플랜으로 충분** (월 $49)

## 🚀 시작하기

### 1. Oxylabs 가입

1. https://oxylabs.io/products/scraper-api/ecommerce/tiktok 방문
2. "Start Free Trial" 클릭
3. 회원가입 (이메일 인증)
4. 7일 무료 평가판 자동 활성화

### 2. API 자격증명 획득

1. Dashboard 로그인
2. **Settings** → **API Users** 이동
3. Username과 Password 확인 (자동 생성됨)

### 3. 프로젝트 설정

`.env` 파일에 자격증명 추가:

```bash
# Oxylabs TikTok Scraper API
OXYLABS_USERNAME=your_username_here
OXYLABS_PASSWORD=your_password_here
```

**그게 끝입니다!** 이제 자동으로 Oxylabs를 사용합니다.

## 📝 사용 예제

### Python 코드

```python
from src.scrapers.social.tiktok_oxylabs import TikTokOxylabs

# Oxylabs 초기화
scraper = TikTokOxylabs()

# 해시태그로 검색
videos = scraper.search_hashtag(
    hashtag="laneige",
    max_videos=30
)

print(f"Found {len(videos)} videos")
for video in videos:
    print(f"- {video['video_id']}: {video['description'][:50]}")
```

### Prefect Flow 실행

```bash
# TikTok 해시태그 검색 (Oxylabs 자동 사용)
python scripts/run_social.py --flow tiktok --hashtag laneige --max 100

# 전체 소셜 미디어 파이프라인
python scripts/run_social.py --flow social-full
```

### 자동 감지 우선순위

시스템은 자동으로 다음 우선순위로 API를 선택합니다:

1. **Oxylabs** (OXYLABS_USERNAME 있으면)
2. **TikTok Research API** (TIKTOK_CLIENT_KEY 있으면)
3. **Playwright** (폴백, 제한적)

## 🔍 수집 가능한 데이터

Oxylabs를 통해 수집 가능:

- ✅ 비디오 ID
- ✅ 비디오 URL
- ✅ 작성자 정보
- ✅ 비디오 설명
- ✅ 해시태그
- ✅ 썸네일 URL
- ⚠️ 메트릭 (조회수, 좋아요 등) - 제한적

**참고:** Oxylabs는 HTML 파싱을 통해 데이터를 수집하므로, 상세 메트릭은 추가 요청이 필요할 수 있습니다.

## 🎯 사용 시나리오

### 시나리오 1: 브랜드 모니터링
```bash
# Laneige 브랜드 모니터링
python scripts/run_social.py --flow tiktok --hashtag laneige --max 100
```

**월 예상 비용:**
- 하루 100개 비디오 = 3,000 요청/월
- Micro 플랜 ($49/월)로 충분

### 시나리오 2: 경쟁사 분석
```python
# 여러 브랜드 해시태그 모니터링
hashtags = ['laneige', 'sulwhasoo', 'innisfree', 'etudehouse']

for tag in hashtags:
    videos = scraper.search_hashtag(tag, max_videos=50)
    # 데이터 저장 및 분석
```

**월 예상 비용:**
- 4개 브랜드 × 50개 비디오 × 30일 = 6,000 요청/월
- Micro 플랜 ($49/월)로 충분

### 시나리오 3: 대규모 데이터 수집
```python
# 대량 데이터 수집
for tag in top_100_beauty_hashtags:
    videos = scraper.search_hashtag(tag, max_videos=100)
```

**월 예상 비용:**
- 100개 태그 × 100개 비디오 × 30일 = 300,000 요청/월
- Starter 플랜 ($149/월) 필요

## ⚙️ 고급 설정

### 1. 프로필 비디오 수집

```python
# 특정 사용자의 비디오 수집
videos = scraper.get_profile_videos(
    username="laneige_kr",
    max_videos=50
)
```

### 2. 로케일 설정

```python
# 한국어 설정
videos = scraper.search_hashtag(
    hashtag="laneige",
    max_videos=30,
    locale="ko-KR"  # 한국어 페이지
)
```

### 3. 배치 처리

```python
# 여러 해시태그 일괄 처리
hashtags = ['laneige', 'laniegelipmask', 'laneigesleepingmask']

all_videos = []
for tag in hashtags:
    videos = scraper.search_hashtag(tag, max_videos=50)
    all_videos.extend(videos)

print(f"Total collected: {len(all_videos)} videos")
```

## 🚨 제한 사항

### 1. Rate Limiting
- Oxylabs는 플랜별로 요청 제한 있음
- 초과시 추가 요금 발생 또는 차단

### 2. 데이터 완전성
- HTML 파싱 기반이므로 TikTok UI 변경시 영향 받을 수 있음
- Oxylabs가 자동으로 파서 업데이트하지만 약간의 지연 가능

### 3. 메트릭 정확도
- 조회수, 좋아요 수는 제한적으로 수집됨
- 정확한 메트릭이 필요하면 추가 구현 필요

## 💡 비용 절감 팁

### 1. 캐싱 활용
```python
# 중복 요청 방지
if not is_cached(hashtag):
    videos = scraper.search_hashtag(hashtag, max_videos=30)
    cache_results(hashtag, videos)
```

### 2. 스케줄링 최적화
```python
# 매일 수집 대신 주간 수집
# 하루 100개 → 주 700개 → 월 3,000개 (Micro 플랜)
```

### 3. 타겟팅 집중
```python
# 상위 해시태그만 집중 모니터링
priority_hashtags = ['laneige', 'laniegelipmask']  # 핵심 2개만
```

## 🆚 대안 비교

### Oxylabs vs 직접 구축 비용

| 항목 | Oxylabs | 직접 구축 |
|------|---------|-----------|
| **개발 시간** | 0시간 | 40-80시간 |
| **개발 비용** | $0 | $2,000-4,000 |
| **월 운영 비용** | $49+ | $0-200 (프록시) |
| **유지보수** | Oxylabs 담당 | 직접 관리 |
| **안정성** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |
| **총 1년 비용** | $588 | $2,000-6,400 |

💡 **결론:** 소규모/중규모 프로젝트는 Oxylabs가 훨씬 경제적

## ❓ FAQ

### Q1: 무료 평가판으로 얼마나 사용 가능한가요?
**A:** 7일 동안 Micro 플랜 전체 기능 사용 가능 (24,500 요청). 하루 3,500 요청까지 테스트 가능.

### Q2: 상업적으로 사용 가능한가요?
**A:** 네, Oxylabs는 상업적 사용 완전 허용. TikTok Research API와 달리 제한 없음.

### Q3: TikTok이 차단하지 않나요?
**A:** Oxylabs가 프록시 로테이션 및 안티봇 회피 기능을 제공하여 차단 위험 최소화.

### Q4: 요청 수가 초과하면 어떻게 되나요?
**A:** 플랜 한도 초과시 자동으로 추가 요금 부과되거나 요청 거부. Dashboard에서 알림 설정 가능.

### Q5: 다른 소셜 미디어도 지원하나요?
**A:** 네, Oxylabs는 Instagram, Facebook, Twitter, LinkedIn 등도 지원.

### Q6: 한국에서도 사용 가능한가요?
**A:** 네, 전 세계 어디서나 사용 가능. 한국 사용자도 많음.

## 📚 참고 자료

- [Oxylabs TikTok Scraper 공식 페이지](https://oxylabs.io/products/scraper-api/ecommerce/tiktok)
- [Oxylabs 가격표](https://oxylabs.io/products/scraper-api/web/pricing)
- [Oxylabs API 문서](https://developers.oxylabs.io/scraping-solutions/web-scraper-api/targets/tiktok)

## 🎉 권장사항

**이런 경우 Oxylabs 추천:**
- ✅ 상업적 브랜드 모니터링
- ✅ 빠른 프로토타입 개발
- ✅ 안정적인 데이터 수집 필요
- ✅ 개발 리소스 부족
- ✅ 소규모~중규모 프로젝트

**이런 경우 직접 구축 고려:**
- ⚠️ 초대규모 수집 (수백만 건)
- ⚠️ 매우 제한된 예산
- ⚠️ 완전한 커스터마이징 필요
- ⚠️ 이미 스크래핑 인프라 있음

---

**구현 완료 날짜:** 2025-12-18
**최종 업데이트:** 2025-12-18

**Sources:**
- [Web Scraper API pricing - Free Trial](https://oxylabs.io/products/scraper-api/web/pricing)
- [TikTok Scraper API | Free Trial](https://oxylabs.io/products/scraper-api/ecommerce/tiktok)
- [Oxylabs Scraper APIs Pricing 2025](https://www.trustradius.com/products/oxylabs/pricing)
