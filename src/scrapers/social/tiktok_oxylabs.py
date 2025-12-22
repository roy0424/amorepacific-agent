"""
TikTok 크롤러 (Oxylabs Scraper API)
Oxylabs TikTok Scraper API 사용 - 승인 필요없이 바로 사용 가능
"""
import os
import requests
from typing import List, Dict, Optional
from datetime import datetime
from loguru import logger
import base64


class TikTokOxylabs:
    """Oxylabs Scraper API를 사용한 TikTok 데이터 수집"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        초기화

        Args:
            username: Oxylabs API username (없으면 환경변수에서 로드)
            password: Oxylabs API password (없으면 환경변수에서 로드)
        """
        self.username = username or os.getenv("OXYLABS_USERNAME")
        self.password = password or os.getenv("OXYLABS_PASSWORD")

        if not self.username or not self.password:
            raise ValueError(
                "Oxylabs credentials not found. Set OXYLABS_USERNAME and OXYLABS_PASSWORD "
                "environment variables."
            )

        self.api_url = "https://realtime.oxylabs.io/v1/queries"
        logger.info("Oxylabs TikTok Scraper initialized")

    def _make_request(self, payload: Dict) -> Dict:
        """
        Oxylabs API 요청 실행

        Args:
            payload: API 요청 페이로드

        Returns:
            API 응답 데이터
        """
        try:
            # Basic Auth 설정
            auth = (self.username, self.password)

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                self.api_url,
                json=payload,
                headers=headers,
                auth=auth,
                timeout=180  # 3분 타임아웃
            )

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            logger.error(f"Oxylabs API request failed: {e}")
            if hasattr(e, 'response') and hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def search_hashtag(
        self,
        hashtag: str,
        max_videos: int = 30,
        locale: str = "en-US"
    ) -> List[Dict]:
        """
        해시태그로 TikTok 비디오 검색

        Args:
            hashtag: 해시태그 (# 포함 또는 미포함)
            max_videos: 최대 수집 비디오 수
            locale: 언어 설정 (예: 'en-US', 'ko-KR')

        Returns:
            비디오 정보 리스트
        """
        clean_hashtag = hashtag.lstrip('#')
        logger.info(f"Searching TikTok via Oxylabs: hashtag=#{clean_hashtag}, max={max_videos}")

        try:
            # TikTok 해시태그 페이지 URL
            url = f"https://www.tiktok.com/tag/{clean_hashtag}"

            payload = {
                "source": "universal",
                "url": url,
                "user_agent_type": "desktop",
                "render": "html",
                "parse": True,
                "parsing_instructions": {
                    "videos": {
                        "_fns": [
                            {
                                "_fn": "xpath",
                                "_args": ["//div[@data-e2e='challenge-item']"]
                            }
                        ],
                        "_items": {
                            "video_url": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//a[contains(@href, '/video/')]/@href"]
                                    }
                                ]
                            },
                            "author": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//a[contains(@href, '/@')]//text()"]
                                    }
                                ]
                            },
                            "description": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//div[@data-e2e='challenge-item-desc']//text()"]
                                    }
                                ]
                            },
                            "thumbnail": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//img/@src"]
                                    }
                                ]
                            }
                        }
                    }
                },
                "locale": locale
            }

            result = self._make_request(payload)

            # 결과 파싱
            videos = []

            # 결과 구조 검증
            if not isinstance(result, dict):
                logger.warning(f"Result is not a dict: {type(result)}")
                return videos

            if "results" not in result:
                logger.warning(f"No 'results' key in response. Keys: {list(result.keys())}")
                return videos

            results_list = result.get("results")
            if not results_list or not isinstance(results_list, list) or len(results_list) == 0:
                logger.warning(f"Results list is empty or invalid: {results_list}")
                return videos

            first_result = results_list[0]
            if first_result is None:
                logger.warning("First result is None, no videos found")
                return videos

            parsed_data = first_result.get("content", {})
            if not parsed_data:
                logger.warning("No content in parsed data")
                return videos

            video_list = parsed_data.get("videos", [])
            if not video_list:
                logger.warning(f"No videos in parsed data. Content keys: {list(parsed_data.keys())}")
                return videos

            for video_data in video_list[:max_videos]:
                parsed_video = self._parse_video(video_data)
                if parsed_video:
                    videos.append(parsed_video)

            logger.info(f"Found {len(videos)} TikTok videos for #{clean_hashtag}")
            return videos

        except Exception as e:
            import traceback
            logger.error(f"Error scraping TikTok hashtag via Oxylabs: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise

    def search_keyword(
        self,
        keyword: str,
        max_videos: int = 30
    ) -> List[Dict]:
        """
        키워드로 TikTok 비디오 검색

        Args:
            keyword: 검색 키워드
            max_videos: 최대 수집 비디오 수

        Returns:
            비디오 정보 리스트
        """
        logger.info(f"Searching TikTok via Oxylabs: keyword='{keyword}', max={max_videos}")

        try:
            # TikTok 검색 URL
            url = f"https://www.tiktok.com/search?q={keyword}"

            payload = {
                "source": "universal",
                "url": url,
                "user_agent_type": "desktop",
                "render": "html",
                "parse": False  # 간단한 HTML 반환
            }

            result = self._make_request(payload)

            # HTML 파싱은 복잡하므로, 기본 구조만 반환
            # 실제 사용시에는 parsing_instructions 추가 필요
            videos = []

            logger.info(f"Search completed for keyword '{keyword}'")
            logger.warning("Keyword search returns raw HTML. Consider using hashtag search instead.")

            return videos

        except Exception as e:
            logger.error(f"Error searching TikTok keyword via Oxylabs: {e}")
            raise

    def get_profile_videos(
        self,
        username: str,
        max_videos: int = 30
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
        logger.info(f"Getting TikTok profile videos via Oxylabs: @{clean_username}, max={max_videos}")

        try:
            url = f"https://www.tiktok.com/@{clean_username}"

            payload = {
                "source": "universal",
                "url": url,
                "user_agent_type": "desktop",
                "render": "html",
                "parse": True,
                "parsing_instructions": {
                    "videos": {
                        "_fns": [
                            {
                                "_fn": "xpath",
                                "_args": ["//div[contains(@class, 'DivItemContainer')]"]
                            }
                        ],
                        "_items": {
                            "video_url": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//a[contains(@href, '/video/')]/@href"]
                                    }
                                ]
                            },
                            "thumbnail": {
                                "_fns": [
                                    {
                                        "_fn": "xpath",
                                        "_args": [".//img/@src"]
                                    }
                                ]
                            }
                        }
                    }
                }
            }

            result = self._make_request(payload)

            videos = []
            if "results" in result and len(result["results"]) > 0:
                first_result = result["results"][0]
                if first_result is None:
                    logger.warning("First result is None, no videos found")
                    return videos

                parsed_data = first_result.get("content", {})
                if not parsed_data:
                    logger.warning("No content in parsed data")
                    return videos

                video_list = parsed_data.get("videos", [])
                if not video_list:
                    logger.warning(f"No videos in parsed data. Content keys: {list(parsed_data.keys())}")
                    return videos

                for video_data in video_list[:max_videos]:
                    parsed_video = self._parse_video(video_data)
                    if parsed_video:
                        parsed_video['author_username'] = clean_username
                        videos.append(parsed_video)

            logger.info(f"Found {len(videos)} videos from @{clean_username}")
            return videos

        except Exception as e:
            logger.error(f"Error getting profile videos via Oxylabs: {e}")
            raise

    def _parse_video(self, video_data: Dict) -> Optional[Dict]:
        """
        Oxylabs 응답을 파싱하여 구조화된 데이터로 변환

        Args:
            video_data: Oxylabs 파싱 결과

        Returns:
            파싱된 비디오 데이터
        """
        try:
            video_url = video_data.get("video_url", "")

            # video_url이 비어있으면 스킵
            if not video_url or "/video/" not in video_url:
                return None

            # 전체 URL 생성
            if video_url.startswith('/'):
                video_url = f"https://www.tiktok.com{video_url}"

            # video_id 추출
            video_id = self._extract_video_id(video_url)
            if not video_id:
                return None

            # 작성자 정보
            author = video_data.get("author", "")
            if isinstance(author, list):
                author = author[0] if author else ""
            author = str(author).lstrip('@').strip()

            # 설명
            description = video_data.get("description", "")
            if isinstance(description, list):
                description = " ".join(description)

            # 썸네일
            thumbnail = video_data.get("thumbnail", "")
            if isinstance(thumbnail, list):
                thumbnail = thumbnail[0] if thumbnail else ""

            # 해시태그 추출
            hashtags = self._extract_hashtags(str(description))

            return {
                'video_id': video_id,
                'video_url': video_url,
                'author_username': author,
                'description': str(description).strip(),
                'hashtags': ','.join(hashtags) if hashtags else None,
                'thumbnail_url': thumbnail,
                'view_count': 0,  # Oxylabs로는 메트릭 수집 제한적
                'like_count': 0,
                'comment_count': 0,
                'share_count': 0,
            }

        except Exception as e:
            logger.warning(f"Error parsing video data: {e}")
            return None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """URL에서 video_id 추출"""
        import re
        match = re.search(r'/video/(\d+)', url)
        if match:
            return match.group(1)
        return None

    def _extract_hashtags(self, text: str) -> List[str]:
        """텍스트에서 해시태그 추출"""
        import re
        if not text:
            return []
        hashtags = re.findall(r'#(\w+)', text)
        return hashtags


# 헬퍼 함수
def search_tiktok_hashtag(hashtag: str, max_videos: int = 30) -> List[Dict]:
    """
    해시태그 검색 헬퍼 함수

    Args:
        hashtag: 해시태그
        max_videos: 최대 비디오 수

    Returns:
        비디오 리스트
    """
    scraper = TikTokOxylabs()
    return scraper.search_hashtag(hashtag, max_videos=max_videos)
