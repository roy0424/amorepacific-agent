# Apify TikTok Scraper 설정 가이드 🚀

**clockworks/tiktok-scraper**를 사용한 TikTok 데이터 수집 방법

## 왜 Apify를 사용하나요? ⭐

- ✅ **가장 안정적**: 전문가가 유지보수, TikTok HTML 변경시 자동 대응
- ✅ **98% 성공률**: 초당 600개 포스트 처리 가능
- ✅ **무료로 시작**: 매월 $5 무료 크레딧 제공
- ✅ **봇 감지 우회**: 프록시 로테이션, 헤더 위장 자동 처리
- ✅ **간편한 통합**: API로 쉽게 연동

## 1단계: Apify 계정 만들기 📝

1. **Apify 회원가입** (무료)
   - 👉 https://console.apify.com/sign-up
   - 신용카드 필요 없음!
   - 매월 $5 무료 크레딧 자동 제공

2. **API 키 발급받기**
   - 로그인 후 https://console.apify.com/account/integrations
   - "Personal API tokens" 섹션에서 API 키 복사
   - 형식: `apify_api_XXXXXXXXXXXXXXXXXXXX`

## 2단계: 프로젝트 설정 ⚙️

### 1) 패키지 설치

```bash
pip install apify-client
```

또는 전체 requirements 설치:

```bash
pip install -r requirements.txt
```

### 2) 환경변수 설정

`.env` 파일에 API 키 추가:

```bash
# TikTok Scraping - Apify
APIFY_API_KEY=apify_api_XXXXXXXXXXXXXXXXXXXX
```

## 3단계: 테스트 실행 🧪

### 간단한 테스트

```bash
python scripts/run_social.py --flow tiktok --hashtag laneige --max 10
```

### 예상 출력

```
21:30:00 | INFO | ✅ Using Apify TikTok Scraper (clockworks/tiktok-scraper)
21:30:01 | INFO | Running Apify actor with input: {'hashtags': ['laneige'], 'resultsPerPage': 10, ...}
21:30:15 | INFO | Found 10 TikTok videos for #laneige
21:30:15 | INFO | Task complete: Scraped 10 TikTok videos via Apify
```

## 가격 정보 💰

### 무료 플랜
- ✅ **매월 $5 무료 크레딧** (자동 갱신)
- ✅ 신용카드 필요 없음
- ✅ 약 1,000개 결과 수집 가능 (월간)

### 비용 예상
- **해시태그 검색**: 1,000개 결과당 약 $5
- **프로필 스크래핑**: 1,000개 비디오당 약 $5
- **PPE (pay-per-event)**: 사용한 만큼만 지불

### 무료 크레딧으로 테스트
```python
# 월 10회 실행, 각 100개 = 1,000개 (무료)
python scripts/run_social.py --flow tiktok --hashtag laneige --max 100
```

## 사용 가능한 기능 🎯

### 1) 해시태그 검색
```python
from src.scrapers.social.tiktok_apify import TikTokApify

scraper = TikTokApify()
videos = scraper.search_hashtag(
    hashtag="laneige",
    max_videos=100,
    min_likes=1000  # 좋아요 1,000개 이상만
)
```

### 2) 프로필 스크래핑
```python
videos = scraper.search_profile(
    username="laneige_kr",
    max_videos=50
)
```

### 3) 키워드 검색
```python
videos = scraper.search_keyword(
    keyword="라네즈 립마스크",
    max_videos=100
)
```

### 4) 날짜 필터
```python
from datetime import datetime, timedelta

videos = scraper.search_hashtag(
    hashtag="laneige",
    max_videos=100,
    date_from=datetime.now() - timedelta(days=7),  # 최근 7일
    date_to=datetime.now()
)
```

## 데이터 구조 📊

수집되는 데이터:

```json
{
  "video_id": "7123456789012345678",
  "video_url": "https://www.tiktok.com/@user/video/7123456789012345678",
  "author_username": "laneige_kr",
  "description": "라네즈 립슬리핑마스크 💙 #laneige #립마스크",
  "hashtags": "laneige,립마스크",
  "thumbnail_url": "https://...",
  "view_count": 123456,
  "like_count": 5678,
  "comment_count": 123,
  "share_count": 45,
  "published_at": "2025-12-18T12:00:00"
}
```

## 트러블슈팅 🔧

### 1) ImportError: No module named 'apify_client'
```bash
pip install apify-client
```

### 2) ValueError: Apify API key not found
`.env` 파일에 `APIFY_API_KEY` 추가 확인

### 3) API 크레딧 부족
- https://console.apify.com/billing 에서 크레딧 확인
- 무료 크레딧은 매월 1일 자동 갱신
- 필요시 유료 플랜 구매

### 4) 결과가 0개 반환
- 해시태그가 실제로 존재하는지 확인
- `min_likes`, `date_from` 등 필터가 너무 엄격한지 확인
- Apify Console에서 실행 로그 확인: https://console.apify.com/actors/runs

## 대안 방법 비교 📊

| 방법 | 안정성 | 비용 | 설정 난이도 | 데이터 품질 |
|------|--------|------|-------------|-------------|
| **Apify** ⭐ | ⭐⭐⭐⭐⭐ | $5/월 (무료) | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| Oxylabs | ⭐⭐⭐ | $49/월 | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Research API | ⭐⭐⭐⭐ | 무료 (승인 필요) | ⭐⭐ | ⭐⭐⭐⭐⭐ |
| Playwright | ⭐⭐ | 무료 | ⭐⭐⭐ | ⭐⭐ |

## 추가 리소스 📚

- 🔗 Apify 콘솔: https://console.apify.com
- 🔗 clockworks/tiktok-scraper: https://apify.com/clockworks/tiktok-scraper
- 🔗 Apify 문서: https://docs.apify.com/api/client/python
- 🔗 가격표: https://apify.com/pricing

## 문의 및 지원 💬

문제가 발생하면:
1. Apify 실행 로그 확인: https://console.apify.com/actors/runs
2. GitHub Issues 등록
3. Apify 지원팀 문의: support@apify.com

---

**Happy Scraping! 🎉**
