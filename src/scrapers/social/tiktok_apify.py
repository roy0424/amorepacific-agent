"""
TikTok 크롤러 (Apify - clockworks/tiktok-scraper)
가장 인기 있고 검증된 Apify TikTok Scraper 사용
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


class TikTokApify:
    """Apify clockworks/tiktok-scraper를 사용한 TikTok 데이터 수집"""

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
        self.actor_id = "clockworks/tiktok-scraper"
        logger.info(f"Apify TikTok Scraper initialized (actor: {self.actor_id})")

    def search_hashtag(
        self,
        hashtag: str,
        max_videos: int = 100,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        min_likes: Optional[int] = None,
        max_likes: Optional[int] = None
    ) -> List[Dict]:
        """
        해시태그로 TikTok 비디오 검색

        Args:
            hashtag: 해시태그 (# 포함 또는 미포함)
            max_videos: 최대 수집 비디오 수
            date_from: 시작 날짜 (선택사항)
            date_to: 종료 날짜 (선택사항)
            min_likes: 최소 좋아요 수 (선택사항)
            max_likes: 최대 좋아요 수 (선택사항)

        Returns:
            비디오 정보 리스트
        """
        clean_hashtag = hashtag.lstrip('#')
        logger.info(f"Searching TikTok via Apify: hashtag=#{clean_hashtag}, max={max_videos}")

        try:
            # Apify Actor 실행 input 구성
            run_input = {
                "hashtags": [clean_hashtag],
                "resultsPerPage": min(max_videos, 1000),  # Apify 권장 최대값
                "shouldDownloadVideos": False,  # 비디오 다운로드는 비용이 많이 듦
                "shouldDownloadCovers": False,
                "shouldDownloadSlideshowImages": False,
                "shouldDownloadSubtitles": False,
            }

            # 날짜 필터 추가
            if date_from:
                run_input["postDateRangeFrom"] = date_from.isoformat()
            if date_to:
                run_input["postDateRangeTo"] = date_to.isoformat()

            # 좋아요 필터 추가
            if min_likes is not None:
                run_input["minHeartCount"] = min_likes
            if max_likes is not None:
                run_input["maxHeartCount"] = max_likes

            logger.info(f"Running Apify actor with input: {run_input}")

            # Actor 실행 (동기 방식)
            run = self.client.actor(self.actor_id).call(run_input=run_input)

            # 결과 가져오기
            videos = []
            dataset_id = run.get("defaultDatasetId")

            if not dataset_id:
                logger.warning("No dataset ID returned from Apify")
                return videos

            # 데이터셋에서 결과 추출
            for item in self.client.dataset(dataset_id).iterate_items():
                parsed_video = self._parse_apify_video(item)
                if parsed_video:
                    videos.append(parsed_video)

                if len(videos) >= max_videos:
                    break

            logger.info(f"Found {len(videos)} TikTok videos for #{clean_hashtag}")
            return videos

        except Exception as e:
            logger.error(f"Error scraping TikTok hashtag via Apify: {e}")
            raise

    def search_profile(
        self,
        username: str,
        max_videos: int = 100
    ) -> List[Dict]:
        """
        사용자 프로필에서 비디오 가져오기

        Args:
            username: TikTok 사용자명 (@ 포함 또는 미포함)
            max_videos: 최대 수집 비디오 수

        Returns:
            비디오 정보 리스트
        """
        clean_username = username.lstrip('@')
        logger.info(f"Getting TikTok profile videos via Apify: @{clean_username}, max={max_videos}")

        try:
            run_input = {
                "profiles": [clean_username],
                "resultsPerPage": min(max_videos, 1000),
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
            }

            run = self.client.actor(self.actor_id).call(run_input=run_input)

            videos = []
            dataset_id = run.get("defaultDatasetId")

            if dataset_id:
                for item in self.client.dataset(dataset_id).iterate_items():
                    parsed_video = self._parse_apify_video(item)
                    if parsed_video:
                        videos.append(parsed_video)

                    if len(videos) >= max_videos:
                        break

            logger.info(f"Found {len(videos)} videos from @{clean_username}")
            return videos

        except Exception as e:
            logger.error(f"Error getting profile videos via Apify: {e}")
            raise

    def search_keyword(
        self,
        keyword: str,
        max_videos: int = 100
    ) -> List[Dict]:
        """
        키워드로 TikTok 비디오 검색

        Args:
            keyword: 검색 키워드
            max_videos: 최대 수집 비디오 수

        Returns:
            비디오 정보 리스트
        """
        logger.info(f"Searching TikTok via Apify: keyword='{keyword}', max={max_videos}")

        try:
            run_input = {
                "searches": [keyword],
                "resultsPerPage": min(max_videos, 1000),
                "shouldDownloadVideos": False,
                "shouldDownloadCovers": False,
            }

            run = self.client.actor(self.actor_id).call(run_input=run_input)

            videos = []
            dataset_id = run.get("defaultDatasetId")

            if dataset_id:
                for item in self.client.dataset(dataset_id).iterate_items():
                    parsed_video = self._parse_apify_video(item)
                    if parsed_video:
                        videos.append(parsed_video)

                    if len(videos) >= max_videos:
                        break

            logger.info(f"Found {len(videos)} TikTok videos for keyword '{keyword}'")
            return videos

        except Exception as e:
            logger.error(f"Error searching TikTok keyword via Apify: {e}")
            raise

    def _parse_apify_video(self, item: Dict) -> Optional[Dict]:
        """
        Apify 응답을 파싱하여 구조화된 데이터로 변환

        Args:
            item: Apify 데이터셋 아이템

        Returns:
            파싱된 비디오 데이터
        """
        try:
            # Apify clockworks/tiktok-scraper 응답 구조
            video_id = item.get("id", "")
            if not video_id:
                return None

            # 작성자 정보
            author_info = item.get("authorMeta", {}) or {}
            author_username = author_info.get("name", "")

            # 비디오 URL
            video_url = item.get("webVideoUrl") or item.get("videoUrl") or f"https://www.tiktok.com/@{author_username}/video/{video_id}"

            # 설명
            description = item.get("text", "") or ""

            # 해시태그 추출
            hashtags = []
            hashtag_list = item.get("hashtags", []) or []
            if hashtag_list:
                hashtags = [tag.get("name", "") for tag in hashtag_list if isinstance(tag, dict)]
            else:
                # 설명에서 해시태그 추출
                import re
                hashtags = re.findall(r'#(\w+)', description)

            # 메트릭
            view_count = item.get("playCount", 0) or 0
            like_count = item.get("diggCount", 0) or item.get("heartCount", 0) or 0
            comment_count = item.get("commentCount", 0) or 0
            share_count = item.get("shareCount", 0) or 0

            # 게시 날짜
            published_at = None
            create_time = item.get("createTime")
            if create_time:
                try:
                    # Unix timestamp or ISO format
                    if isinstance(create_time, (int, float)):
                        published_at = datetime.fromtimestamp(create_time)
                    else:
                        published_at = datetime.fromisoformat(str(create_time).replace('Z', '+00:00'))
                except Exception as e:
                    logger.debug(f"Error parsing create_time: {e}")

            # 썸네일
            thumbnail_url = item.get("videoMeta", {}).get("coverUrl") if isinstance(item.get("videoMeta"), dict) else None

            return {
                'video_id': str(video_id),
                'video_url': video_url,
                'author_username': author_username,
                'description': description,
                'hashtags': ','.join(hashtags) if hashtags else None,
                'thumbnail_url': thumbnail_url,
                'view_count': view_count,
                'like_count': like_count,
                'comment_count': comment_count,
                'share_count': share_count,
                'published_at': published_at,
            }

        except Exception as e:
            logger.warning(f"Error parsing Apify video data: {e}")
            return None


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
    scraper = TikTokApify()
    return scraper.search_hashtag(hashtag, max_videos=max_videos)
