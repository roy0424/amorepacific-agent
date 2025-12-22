# TikTok Research API 사용 가이드

## 📌 개요

TikTok Research API는 TikTok의 공식 API로, 연구 목적으로 비디오 데이터에 접근할 수 있습니다.

이 프로젝트는 **두 가지 TikTok 크롤링 방법**을 지원합니다:
1. **TikTok Research API** (공식, 권장) - API 키 필요
2. **Playwright 웹 스크래핑** (비공식, 백업) - API 키 없이 동작 (제한적)

## 🔑 TikTok Research API 신청 방법

### 1. 자격 요건

⚠️ **중요: Research API는 연구 목적으로만 사용 가능합니다**

**필수 조건:**
- 대학교 또는 연구 기관 소속
- 비상업적/비영리 연구 목적
- 전문 이메일 주소 (대학교/연구기관 이메일)
- 윤리 심사 통과 증명
- 명확한 연구 계획서

**제외 대상:**
- 크리에이터, 광고주, 상업적 사용자
- 영리 목적 데이터 수집

**지역 제한:**
- 현재 미국과 유럽만 신청 가능

### 2. 신청 절차

#### Step 1: TikTok for Developers 계정 생성
1. https://developers.tiktok.com/ 방문
2. 전문 이메일로 회원가입 (예: @university.edu)
3. Ph.D. 후보자는 지도교수 추천서 필요

#### Step 2: Research API 신청
1. https://developers.tiktok.com/products/research-api/ 접속
2. "Apply for Access" 클릭
3. 연구 계획서 제출:
   - 연구 목적
   - 데이터 사용 계획
   - 윤리 심사 증명서
   - 데이터 보안 계획

#### Step 3: 승인 대기
- 승인까지 수 주 소요 가능
- 추가 정보 요청 가능성 있음

#### Step 4: API 자격증명 획득
승인 후:
1. Developer Dashboard에서 앱 생성
2. Client Key와 Client Secret 발급받기

### 3. API 제한사항

- **일일 요청 제한:** 1,000 요청/일
- **일일 데이터 제한:** 최대 100,000 레코드/일
- **날짜 범위:** 최대 30일
- **페이지 크기:** 최대 100개 비디오/요청
- **협업자:** 최대 9명 추가 가능

## ⚙️ 설정 방법

### 1. API 자격증명 설정

`.env` 파일에 TikTok API 자격증명 추가:

```bash
# TikTok Research API
TIKTOK_CLIENT_KEY=your_client_key_here
TIKTOK_CLIENT_SECRET=your_client_secret_here
```

### 2. 자동 감지 기능

**API 키가 있을 때:**
- 자동으로 TikTok Research API 사용
- 안정적이고 빠른 데이터 수집
- 공식 API로 차단 위험 없음

**API 키가 없을 때:**
- Playwright 웹 스크래핑으로 자동 전환
- 제한적이지만 작동 (headless 모드는 차단됨)

## 📝 사용 예제

### Python 코드

```python
from src.scrapers.social.tiktok_api import TikTokResearchAPI

# API 초기화
api = TikTokResearchAPI()

# 해시태그로 검색
videos = api.search_videos_by_hashtag(
    hashtag="laneige",
    max_count=100,
    days_back=30
)

print(f"Found {len(videos)} videos")
for video in videos:
    print(f"- {video['video_id']}: {video['description']}")
```

### Prefect Flow 실행

```bash
# TikTok 해시태그 검색 (API 자동 감지)
python scripts/run_social.py --flow tiktok --hashtag laneige --max 100

# 전체 소셜 미디어 파이프라인
python scripts/run_social.py --flow social-full
```

## 🔍 수집 가능한 데이터

TikTok Research API를 통해 수집 가능한 정보:

- ✅ 비디오 ID
- ✅ 작성자 정보
- ✅ 비디오 설명
- ✅ 해시태그 목록
- ✅ 조회수, 좋아요, 댓글, 공유 수
- ✅ 비디오 길이
- ✅ 썸네일 URL
- ✅ 생성일
- ✅ 지역 코드

## 🚨 제한 사항 및 주의사항

### 1. 연구 윤리
- 개인정보 보호 필수
- 데이터 사용 목적 준수
- TikTok Terms of Service 준수

### 2. 기술적 제한
- 30일 이상 과거 데이터 불가
- 삭제되거나 비공개된 비디오는 반환 안 됨
- Rate limiting 존재

### 3. 상업적 사용 불가
- Research API는 비상업적 연구 목적만 허용
- 마케팅, 광고, 상업적 분석 불가
- 위반 시 API 접근 차단

## 🆚 API vs 웹 스크래핑 비교

| 기능 | Research API | Playwright 스크래핑 |
|-----|-------------|-------------------|
| **안정성** | ✅ 매우 안정적 | ⚠️ 불안정 (차단 위험) |
| **속도** | ✅ 빠름 | ❌ 느림 |
| **데이터 품질** | ✅ 완전한 메타데이터 | ⚠️ 제한적 |
| **승인 필요** | ⚠️ 필요 (연구자만) | ✅ 불필요 |
| **비용** | ✅ 무료 (제한 있음) | ✅ 무료 |
| **Headless 지원** | ✅ 지원 | ❌ 차단됨 |
| **상업적 사용** | ❌ 불가 | ⚠️ 그레이존 |

## 📚 참고 자료

- [TikTok Research API 공식 문서](https://developers.tiktok.com/doc/research-api-specs-query-videos)
- [TikTok Research API FAQ](https://developers.tiktok.com/doc/research-api-faq)
- [TikTok Developer Portal](https://developers.tiktok.com/)
- [Research API Terms of Service](https://www.tiktok.com/legal/page/global/terms-of-service-research-api/en)

## ❓ FAQ

### Q1: 상업적 목적으로 사용할 수 있나요?
**A:** 아니요. Research API는 비상업적 연구 목적으로만 사용 가능합니다. 브랜드 모니터링이 "연구"로 인정받기는 어렵습니다.

### Q2: 승인 없이 테스트할 수 있나요?
**A:** 코드는 구현되어 있지만, 실제 데이터를 수집하려면 TikTok의 승인과 API 키가 필요합니다.

### Q3: API 키 없이 TikTok 데이터를 수집할 수 있나요?
**A:** Playwright 웹 스크래핑을 사용할 수 있지만, headless 모드가 차단되어 매우 제한적입니다.

### Q4: 한국에서 신청 가능한가요?
**A:** 현재는 미국과 유럽만 지원됩니다. 향후 확대 가능성 있음.

### Q5: 일반 TikTok Display API는 어떤가요?
**A:** Display API는 해시태그 검색 기능이 제한적입니다. 비디오 데이터 수집에는 Research API가 적합합니다.

## 💡 권장사항

**연구자인 경우:**
- TikTok Research API 신청 ✅
- 안정적이고 완전한 데이터 수집 가능

**일반 사용자/상업적 목적:**
- 대안 검토 필요
- 공식 API 대신 다른 소셜 미디어 플랫폼 고려
- YouTube API (공식, 안정적)
- Instagram Basic Display API (제한적)

---

**구현 완료 날짜:** 2025-12-18
**최종 업데이트:** 2025-12-18
