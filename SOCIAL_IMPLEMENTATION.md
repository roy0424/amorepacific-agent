# 소셜미디어 크롤링 구현 완료

Phase 2 소셜미디어 통합이 완료되었습니다!

## ✅ 구현된 기능

### 1. 데이터베이스 모델 (src/models/social_media.py)
- **YouTube**: `youtube_videos`, `youtube_metrics`
- **TikTok**: `tiktok_posts`, `tiktok_metrics`
- **Instagram**: `instagram_posts`, `instagram_metrics`

각 플랫폼마다:
- 포스트/영상 마스터 테이블 (고유 ID, 메타데이터)
- 시계열 메트릭 테이블 (조회수, 좋아요, 댓글 등)

### 2. 크롤러 구현 (src/scrapers/social/)

#### YouTube (youtube.py)
- YouTube Data API v3 공식 API 사용
- 키워드 검색, 해시태그 검색, 채널 영상 조회
- 영상 메트릭 수집: 조회수, 좋아요, 댓글, 발행일
- API 할당량 관리 (10,000 units/day)

```python
from src.scrapers.social.youtube import YouTubeScraper

scraper = YouTubeScraper(api_key="YOUR_KEY")
videos = scraper.search_videos(query="laneige", max_results=50)
```

#### TikTok (tiktok.py)
- Playwright 웹 크롤링 (공식 API 제한적)
- 해시태그 검색 지원
- 영상 메트릭 수집: 조회수, 좋아요, 댓글, 공유
- 봇 차단 회피 메커니즘 내장

```python
from src.scrapers.social.tiktok import TikTokScraper

async with TikTokScraper() as scraper:
    videos = await scraper.search_hashtag(hashtag="laneige", max_videos=30)
```

#### Instagram (instagram.py)
- Instaloader 라이브러리 사용
- 해시태그 검색, 프로필 포스트 조회
- 포스트 메트릭 수집: 좋아요, 댓글, 영상 조회수
- 로그인 선택 (더 많은 데이터 접근)

```python
from src.scrapers.social.instagram import InstagramScraper

scraper = InstagramScraper()
posts = scraper.search_hashtag(hashtag="laneige", max_posts=50)
```

### 3. Prefect Tasks (src/tasks/social_tasks.py)
- `scrape_youtube_videos_task`: YouTube 영상 수집
- `scrape_youtube_hashtag_task`: YouTube 해시태그 검색
- `scrape_tiktok_hashtag_task`: TikTok 해시태그 검색
- `scrape_instagram_hashtag_task`: Instagram 해시태그 검색
- `scrape_instagram_profile_task`: Instagram 프로필 조회
- `scrape_all_social_platforms_task`: 모든 플랫폼 동시 수집

각 태스크:
- 자동 재시도 (3회)
- 타임아웃 설정 (300초)
- 구조화된 로깅

### 4. 데이터 처리 Tasks (src/tasks/processing_tasks.py)
- `save_youtube_videos_to_db_task`: YouTube 데이터 DB 저장
- `save_tiktok_videos_to_db_task`: TikTok 데이터 DB 저장
- `save_instagram_posts_to_db_task`: Instagram 데이터 DB 저장
- `save_all_social_media_to_db_task`: 모든 플랫폼 데이터 일괄 저장

기능:
- 중복 체크 (video_id, shortcode 기준)
- 브랜드 자동 매칭
- 시계열 메트릭 저장
- 트랜잭션 처리

### 5. Prefect Flows (src/flows/social_flow.py)

#### 메인 파이프라인
```python
@flow(name="social-scraping-pipeline")
async def social_pipeline(brand_keywords, hashtags, max_items_per_platform=50)
```
- 모든 플랫폼 동시 크롤링
- DB 자동 저장
- 실행 통계 반환

#### 테스트 파이프라인
```python
@flow(name="social-test-pipeline")
async def social_test_pipeline()
```
- 플랫폼당 10개 아이템만 수집
- 빠른 테스트용

#### 개별 플랫폼 Flows
- `youtube_flow`: YouTube만 크롤링
- `tiktok_flow`: TikTok만 크롤링
- `instagram_flow`: Instagram만 크롤링

### 6. 실행 스크립트 (scripts/run_social.py)
편리한 CLI 인터페이스:

```bash
# 테스트 실행 (10개 아이템)
python scripts/run_social.py --flow social-test

# 전체 파이프라인 (50개 아이템)
python scripts/run_social.py --flow social-full

# YouTube만
python scripts/run_social.py --flow youtube --query laneige --max 30

# TikTok만
python scripts/run_social.py --flow tiktok --hashtag laneige --max 20

# Instagram만
python scripts/run_social.py --flow instagram --hashtag laneige --max 30
```

## 📦 의존성 업데이트

### requirements.txt에 추가됨
```
google-api-python-client==2.154.0  # YouTube API
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
isodate==0.7.2  # YouTube duration parsing
instaloader==4.13.1  # Instagram
```

### .env.example에 이미 포함됨
```
YOUTUBE_API_KEY=AIzaSy-your-youtube-api-key-here
INSTAGRAM_USERNAME=
INSTAGRAM_PASSWORD=
```

## 🚀 사용 방법

### 1. 환경 설정
```bash
# YouTube API 키 발급
# https://console.cloud.google.com/apis/credentials

# .env 파일 수정
YOUTUBE_API_KEY=your-actual-api-key
```

### 2. DB 초기화 (소셜미디어 테이블 생성)
```bash
python scripts/init_db.py
```

### 3. 테스트 실행
```bash
# 빠른 테스트 (10개 아이템)
python scripts/run_social.py --flow social-test
```

### 4. Prefect로 스케줄링 (향후)
```python
from src.flows.social_flow import social_pipeline

# Deploy to Prefect
social_pipeline.serve(
    name="social-media-scraper",
    cron="0 */6 * * *"  # 6시간마다 실행
)
```

## 📊 데이터 구조

### YouTube 예시
```python
{
    'video_id': 'dQw4w9WgXcQ',
    'title': 'Laneige Lip Sleeping Mask Review',
    'channel_title': 'Beauty Blogger',
    'view_count': 125000,
    'like_count': 3500,
    'comment_count': 245,
    'published_at': datetime(2024, 1, 15)
}
```

### TikTok 예시
```python
{
    'video_id': '1234567890123456789',
    'author_username': 'beauty_guru',
    'description': 'Love this #laneige lip mask! #kbeauty',
    'hashtags': 'laneige,kbeauty',
    'view_count': 450000,
    'like_count': 12000,
    'comment_count': 340
}
```

### Instagram 예시
```python
{
    'shortcode': 'CxYzAbc1234',
    'owner_username': 'skincare_addict',
    'caption': 'My favorite #laneige products!',
    'hashtags': 'laneige,kbeauty,skincare',
    'like_count': 2500,
    'comment_count': 85,
    'media_type': 'photo'
}
```

## 🔍 다음 단계

### Prefect 스케줄링 통합
```python
# 소셜미디어 크롤링을 6시간마다 자동 실행
# scripts/deploy_flows.py에 추가 필요

from src.flows.social_flow import social_pipeline

if __name__ == "__main__":
    social_pipeline.serve(
        name="social-media-pipeline",
        cron="0 */6 * * *"
    )
```

### 데이터 분석
- 소셜미디어 메트릭과 아마존 랭킹 상관관계 분석
- 바이럴 모멘트 감지 (급격한 조회수 증가)
- 인플루언서 영향력 분석

### AI 인사이트 (Phase 3)
- GPT-4로 소셜미디어 트렌드 분석
- 랭킹 변동과 바이럴 콘텐츠 연관성 발견
- 예측 모델: 소셜 활동 → 랭킹 예측

## 🎯 검증 체크리스트

- [x] YouTube 크롤러 구현 및 API 연동
- [x] TikTok 크롤러 구현 (Playwright)
- [x] Instagram 크롤러 구현 (Instaloader)
- [x] 소셜미디어 DB 모델 생성
- [x] Prefect Tasks 작성
- [x] Prefect Flows 작성
- [x] DB 저장 로직 구현
- [x] 실행 스크립트 작성
- [x] requirements.txt 업데이트
- [ ] YouTube API 키 발급 및 테스트
- [ ] TikTok 크롤러 실제 테스트
- [ ] Instagram 크롤러 실제 테스트
- [ ] Prefect 스케줄링 통합
- [ ] 6시간마다 자동 실행 검증

## 📝 주요 특징

1. **모듈화된 설계**: 각 플랫폼별 독립적인 크롤러
2. **에러 핸들링**: 자동 재시도 및 로깅
3. **데이터 무결성**: 중복 체크 및 트랜잭션
4. **확장성**: 새로운 플랫폼 추가 용이
5. **테스트 용이성**: 개별 플랫폼 테스트 가능

## 🛠️ 트러블슈팅

### YouTube API 할당량 초과
- 기본 할당량: 10,000 units/day
- search.list: 100 units per call
- 해결: max_results 줄이기, 검색 쿼리 최적화

### TikTok 크롤링 실패
- TikTok은 봇 차단이 강력함
- headless=False로 실행하여 CAPTCHA 수동 해결
- User-Agent 로테이션 활성화

### Instagram 로그인 필요
- 로그인 없이도 제한적 데이터 수집 가능
- 더 많은 데이터: .env에 계정 정보 설정
- 2FA 계정은 앱 비밀번호 사용

---

**구현 완료일**: 2025-12-18
**다음 Phase**: AI 인사이트 생성 (Phase 3)
