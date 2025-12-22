"""
TikTok Research API 크롤러
TikTok 공식 Research API 사용

IMPORTANT: This API requires special approval from TikTok.

Required Scopes:
- research.data.basic: Access to basic research data
- research.video.list: Access to video list data
- research.video.query: Access to video query endpoint

How to get approved:
1. Apply at: https://developers.tiktok.com/products/research-api/
2. Your app must be approved for research purposes
3. After approval, ensure your app has the required scopes enabled
4. If you get 401 "scope_not_authorized" error, check your app settings in TikTok Developer Portal
   and request the necessary research scopes

Common Error:
- 401 Unauthorized with "scope_not_authorized": Your app exists but doesn't have research API scopes.
  You need to apply for Research API access separately from the standard API.
"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from loguru import logger


class TikTokResearchAPI:
    """TikTok Research API를 사용한 비디오 검색"""

    def __init__(self, client_key: Optional[str] = None, client_secret: Optional[str] = None):
        """
        초기화

        Args:
            client_key: TikTok API Client Key (없으면 환경변수에서 로드)
            client_secret: TikTok API Client Secret (없으면 환경변수에서 로드)
        """
        self.client_key = client_key or os.getenv("TIKTOK_CLIENT_KEY")
        self.client_secret = client_secret or os.getenv("TIKTOK_CLIENT_SECRET")

        if not self.client_key or not self.client_secret:
            raise ValueError(
                "TikTok API credentials not found. Set TIKTOK_CLIENT_KEY and TIKTOK_CLIENT_SECRET "
                "environment variables."
            )

        self.base_url = "https://open.tiktokapis.com/v2"
        self.access_token = None
        self._authenticate()

        logger.info("TikTok Research API client initialized")

    def _authenticate(self):
        """OAuth 2.0 Client Credentials로 인증"""
        try:
            url = f"{self.base_url}/oauth/token/"

            headers = {
                "Content-Type": "application/x-www-form-urlencoded"
            }

            data = {
                "client_key": self.client_key,
                "client_secret": self.client_secret,
                "grant_type": "client_credentials"
            }

            response = requests.post(url, headers=headers, data=data)
            response.raise_for_status()

            result = response.json()
            self.access_token = result.get("access_token")

            if not self.access_token:
                raise ValueError("Failed to obtain access token")

            logger.info("Successfully authenticated with TikTok Research API")

        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok API authentication failed: {e}")
            raise

    def search_videos_by_hashtag(
        self,
        hashtag: str,
        max_count: int = 100,
        days_back: int = 30,
        region_code: Optional[str] = None
    ) -> List[Dict]:
        """
        해시태그로 비디오 검색

        Args:
            hashtag: 해시태그 (# 제외)
            max_count: 최대 수집 비디오 수 (최대 100)
            days_back: 며칠 전까지 검색할지 (최대 30일)
            region_code: 지역 코드 (예: 'US', 'KR')

        Returns:
            비디오 정보 리스트
        """
        clean_hashtag = hashtag.lstrip('#')

        # 날짜 범위 계산
        end_date = datetime.now()
        start_date = end_date - timedelta(days=min(days_back, 30))

        logger.info(f"Searching TikTok API: hashtag=#{clean_hashtag}, max={max_count}, "
                   f"date_range={start_date.date()} to {end_date.date()}")

        try:
            url = f"{self.base_url}/research/video/query/"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            # 쿼리 조건 구성
            query_conditions = {
                "and": [
                    {
                        "field_name": "hashtag_name",
                        "operation": "EQ",
                        "field_values": [clean_hashtag]
                    },
                    {
                        "field_name": "create_date",
                        "operation": "GTE",
                        "field_values": [int(start_date.timestamp())]
                    },
                    {
                        "field_name": "create_date",
                        "operation": "LTE",
                        "field_values": [int(end_date.timestamp())]
                    }
                ]
            }

            # 지역 필터 추가 (선택사항)
            if region_code:
                query_conditions["and"].append({
                    "field_name": "region_code",
                    "operation": "EQ",
                    "field_values": [region_code]
                })

            payload = {
                "query": query_conditions,
                "max_count": min(max_count, 100),  # API 최대 100개 제한
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d")
            }

            videos = []
            has_more = True
            cursor = None

            # 페이지네이션으로 모든 결과 가져오기
            while has_more and len(videos) < max_count:
                if cursor:
                    payload["cursor"] = cursor

                response = requests.post(url, headers=headers, json=payload)
                response.raise_for_status()

                result = response.json()

                # 응답에서 비디오 추출
                data = result.get("data", {})
                video_list = data.get("videos", [])

                for video in video_list:
                    parsed_video = self._parse_video(video)
                    videos.append(parsed_video)

                    if len(videos) >= max_count:
                        break

                # 다음 페이지 확인
                has_more = data.get("has_more", False)
                cursor = data.get("cursor")

                if not has_more:
                    break

            logger.info(f"Found {len(videos)} TikTok videos for #{clean_hashtag}")
            return videos

        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok API request failed: {e}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def search_videos_by_keyword(
        self,
        keyword: str,
        max_count: int = 100,
        days_back: int = 30
    ) -> List[Dict]:
        """
        키워드로 비디오 검색

        Args:
            keyword: 검색 키워드
            max_count: 최대 수집 비디오 수
            days_back: 며칠 전까지 검색할지

        Returns:
            비디오 정보 리스트
        """
        end_date = datetime.now()
        start_date = end_date - timedelta(days=min(days_back, 30))

        logger.info(f"Searching TikTok API: keyword='{keyword}', max={max_count}")

        try:
            url = f"{self.base_url}/research/video/query/"

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }

            query_conditions = {
                "and": [
                    {
                        "field_name": "keyword",
                        "operation": "IN",
                        "field_values": [keyword]
                    },
                    {
                        "field_name": "create_date",
                        "operation": "GTE",
                        "field_values": [int(start_date.timestamp())]
                    },
                    {
                        "field_name": "create_date",
                        "operation": "LTE",
                        "field_values": [int(end_date.timestamp())]
                    }
                ]
            }

            payload = {
                "query": query_conditions,
                "max_count": min(max_count, 100),
                "start_date": start_date.strftime("%Y%m%d"),
                "end_date": end_date.strftime("%Y%m%d")
            }

            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()

            result = response.json()
            data = result.get("data", {})
            video_list = data.get("videos", [])

            videos = [self._parse_video(video) for video in video_list]

            logger.info(f"Found {len(videos)} TikTok videos for keyword '{keyword}'")
            return videos

        except requests.exceptions.RequestException as e:
            logger.error(f"TikTok API request failed: {e}")
            raise

    def _parse_video(self, video: Dict) -> Dict:
        """
        TikTok API 응답을 파싱하여 구조화된 데이터로 변환

        Args:
            video: TikTok API 응답 비디오 객체

        Returns:
            파싱된 비디오 데이터
        """
        # 생성일 파싱
        create_time = video.get("create_time")
        published_at = None
        if create_time:
            try:
                published_at = datetime.fromtimestamp(create_time)
            except Exception:
                pass

        # 해시태그 추출
        hashtags = video.get("hashtag_names", [])
        hashtags_str = ','.join(hashtags) if hashtags else None

        # 비디오 ID
        video_id = video.get("id", "")

        return {
            'video_id': video_id,
            'video_url': f"https://www.tiktok.com/@{video.get('username', 'user')}/video/{video_id}",
            'author_username': video.get("username", ""),
            'description': video.get("video_description", ""),
            'hashtags': hashtags_str,
            'thumbnail_url': video.get("cover_image_url"),
            'view_count': video.get("view_count", 0),
            'like_count': video.get("like_count", 0),
            'comment_count': video.get("comment_count", 0),
            'share_count': video.get("share_count", 0),
            'duration_seconds': video.get("duration", 0),
            'published_at': published_at,
            'region_code': video.get("region_code"),
        }


# 헬퍼 함수
def search_tiktok_hashtag(hashtag: str, max_videos: int = 100) -> List[Dict]:
    """
    해시태그 검색 헬퍼 함수

    Args:
        hashtag: 해시태그
        max_videos: 최대 비디오 수

    Returns:
        비디오 리스트
    """
    api = TikTokResearchAPI()
    return api.search_videos_by_hashtag(hashtag, max_count=max_videos)
