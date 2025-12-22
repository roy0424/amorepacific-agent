"""
Instagram 크롤러 (Apify - instagram-scraper)
가장 인기 있고 검증된 Apify Instagram Scraper 사용
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger

try:
    from apify_client import ApifyClient
    APIFY_AVAILABLE = True
except ImportError:
    APIFY_AVAILABLE = False
    logger.warning("apify-client not installed. Run: pip install apify-client")


class InstagramApify:
    """Apify instagram-scraper를 사용한 Instagram 데이터 수집"""

    def __init__(self, api_key: Optional[str] = None):
        """
        초기화

        Args:
            api_key: Apify API Key (없으면 환경변수에서 로드)
        """
        if not APIFY_AVAILABLE:
            raise ImportError(
                "apify-client is not installed. "
                "Install it with: pip install apify-client"
            )

        self.api_key = api_key or os.getenv("APIFY_API_KEY")

        if not self.api_key:
            raise ValueError(
                "Apify API key not found. Set APIFY_API_KEY environment variable or pass it to constructor.\n"
                "Get your API key at: https://console.apify.com/account/integrations"
            )

        self.client = ApifyClient(self.api_key)
        self.actor_id = "apify/instagram-hashtag-scraper"
        logger.info(f"Apify Instagram Hashtag Scraper initialized (actor: {self.actor_id})")

    def search_hashtag(
        self,
        hashtag: str,
        max_posts: int = 100,
    ) -> List[Dict]:
        """
        해시태그로 Instagram 포스트 검색

        Args:
            hashtag: 해시태그 (# 포함 또는 미포함)
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        clean_hashtag = hashtag.lstrip('#')
        logger.info(f"Searching Instagram via Apify: hashtag=#{clean_hashtag}, max={max_posts}")

        try:
            # Apify Actor 실행 input 구성
            run_input = {
                "hashtags": [clean_hashtag],
                "resultsType": "posts",
                "resultsLimit": max_posts,
            }

            logger.info(f"Running Apify actor with input: {run_input}")

            # Actor 실행 (동기 방식)
            run = self.client.actor(self.actor_id).call(run_input=run_input)

            # 결과 가져오기
            posts = []
            dataset_id = run.get("defaultDatasetId")

            if not dataset_id:
                logger.warning("No dataset ID returned from Apify")
                return posts

            # 데이터셋에서 결과 추출
            for item in self.client.dataset(dataset_id).iterate_items():
                parsed_post = self._parse_apify_post(item)
                if parsed_post:
                    posts.append(parsed_post)

                if len(posts) >= max_posts:
                    break

            logger.info(f"Found {len(posts)} Instagram posts for #{clean_hashtag}")
            return posts

        except Exception as e:
            logger.error(f"Error scraping Instagram hashtag via Apify: {e}")
            raise

    def search_profile(
        self,
        username: str,
        max_posts: int = 100
    ) -> List[Dict]:
        """
        사용자 프로필에서 포스트 가져오기

        Note: 프로필 스크래핑은 apify/instagram-scraper 사용

        Args:
            username: Instagram 사용자명 (@ 포함 또는 미포함)
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        clean_username = username.lstrip('@')
        logger.info(f"Getting Instagram profile posts via Apify: @{clean_username}, max={max_posts}")

        try:
            # 프로필용은 일반 instagram-scraper 사용
            run_input = {
                "usernames": [clean_username],
                "resultsLimit": max_posts,
            }

            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)

            posts = []
            dataset_id = run.get("defaultDatasetId")

            if dataset_id:
                for item in self.client.dataset(dataset_id).iterate_items():
                    parsed_post = self._parse_apify_post(item)
                    if parsed_post:
                        posts.append(parsed_post)

                    if len(posts) >= max_posts:
                        break

            logger.info(f"Found {len(posts)} posts from @{clean_username}")
            return posts

        except Exception as e:
            logger.error(f"Error getting profile posts via Apify: {e}")
            raise

    def search_location(
        self,
        location_id: str,
        max_posts: int = 100
    ) -> List[Dict]:
        """
        위치 태그로 포스트 검색

        Note: 위치 스크래핑은 apify/instagram-scraper 사용

        Args:
            location_id: Instagram 위치 ID
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        logger.info(f"Searching Instagram location via Apify: location_id={location_id}, max={max_posts}")

        try:
            # 위치용은 일반 instagram-scraper 사용
            run_input = {
                "directUrls": [f"https://www.instagram.com/explore/locations/{location_id}/"],
                "resultsLimit": max_posts,
            }

            run = self.client.actor("apify/instagram-scraper").call(run_input=run_input)

            posts = []
            dataset_id = run.get("defaultDatasetId")

            if dataset_id:
                for item in self.client.dataset(dataset_id).iterate_items():
                    parsed_post = self._parse_apify_post(item)
                    if parsed_post:
                        posts.append(parsed_post)

                    if len(posts) >= max_posts:
                        break

            logger.info(f"Found {len(posts)} posts for location {location_id}")
            return posts

        except Exception as e:
            logger.error(f"Error searching location via Apify: {e}")
            raise

    def _parse_apify_post(self, item: Dict) -> Optional[Dict]:
        """
        Apify 응답을 파싱하여 구조화된 데이터로 변환

        Args:
            item: Apify 데이터셋 아이템

        Returns:
            파싱된 포스트 데이터
        """
        try:
            # Shortcode (post ID)
            shortcode = item.get("shortCode") or item.get("id", "")
            if not shortcode:
                return None

            # 포스트 URL
            post_url = item.get("url") or f"https://www.instagram.com/p/{shortcode}/"

            # 작성자 정보
            owner_username = item.get("ownerUsername", "")

            # 캡션
            caption = item.get("caption", "") or ""

            # 해시태그 추출
            hashtags = []
            if item.get("hashtags"):
                hashtags = item.get("hashtags", [])
            else:
                # 캡션에서 해시태그 추출
                import re
                hashtags = re.findall(r'#(\w+)', caption)

            # 미디어 타입
            type_name = item.get("type", "")
            if type_name == "Video":
                media_type = "video"
            elif type_name == "Sidecar":
                media_type = "carousel"
            else:
                media_type = "photo"

            # 메트릭
            like_count = item.get("likesCount", 0) or 0
            comment_count = item.get("commentsCount", 0) or 0

            # 비디오 조회수 (비디오인 경우만)
            video_view_count = None
            if media_type == "video":
                video_view_count = item.get("videoViewCount") or item.get("videoPlayCount")

            # 게시 날짜
            posted_at = None
            timestamp = item.get("timestamp")
            if timestamp:
                try:
                    posted_at = datetime.fromisoformat(str(timestamp).replace('Z', '+00:00'))
                except Exception as e:
                    logger.debug(f"Error parsing timestamp: {e}")

            # 미디어 URL
            media_url = item.get("displayUrl") or item.get("url")

            return {
                'shortcode': shortcode,
                'owner_username': owner_username,
                'owner_id': str(item.get("ownerId", "")),
                'caption': caption,
                'hashtags': ','.join(hashtags) if hashtags else None,
                'post_url': post_url,
                'media_type': media_type,
                'media_url': media_url,
                'posted_at': posted_at,
                'like_count': like_count,
                'comment_count': comment_count,
                'video_view_count': video_view_count,
            }

        except Exception as e:
            logger.warning(f"Error parsing Apify Instagram post data: {e}")
            return None


# 헬퍼 함수
def search_instagram_hashtag(hashtag: str, max_posts: int = 100) -> List[Dict]:
    """
    해시태그 검색 헬퍼 함수

    Args:
        hashtag: 해시태그
        max_posts: 최대 포스트 수

    Returns:
        포스트 리스트
    """
    scraper = InstagramApify()
    return scraper.search_hashtag(hashtag, max_posts=max_posts)
