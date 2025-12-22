"""
Instagram 크롤러
Instaloader 라이브러리 사용
"""
import os
from typing import List, Dict, Optional
from datetime import datetime
import instaloader
from loguru import logger


class InstagramScraper:
    """Instaloader를 사용한 Instagram 해시태그 및 포스트 크롤링"""

    def __init__(self, username: Optional[str] = None, password: Optional[str] = None):
        """
        초기화

        Args:
            username: Instagram 계정 (선택, 로그인하면 더 많은 데이터 접근 가능)
            password: Instagram 비밀번호
        """
        self.loader = instaloader.Instaloader(
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            post_metadata_txt_pattern='',
            quiet=True  # 불필요한 출력 줄이기
        )

        # 로그인 (선택)
        self.logged_in = False
        if username and password:
            try:
                self.loader.login(username, password)
                self.logged_in = True
                logger.info(f"Instagram logged in as: {username}")
            except Exception as e:
                logger.warning(f"Instagram login failed: {e}. Continuing without login.")

        logger.info("Instagram scraper initialized")

    def search_hashtag(
        self,
        hashtag: str,
        max_posts: int = 50
    ) -> List[Dict]:
        """
        해시태그로 포스트 검색

        Args:
            hashtag: 해시태그 (# 제외)
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        clean_tag = hashtag.lstrip('#')
        logger.info(f"Searching Instagram hashtag: #{clean_tag}, max_posts={max_posts}")

        posts = []

        try:
            # 해시태그로 포스트 가져오기
            hashtag_posts = instaloader.Hashtag.from_name(
                self.loader.context,
                clean_tag
            ).get_posts()

            count = 0
            for post in hashtag_posts:
                if count >= max_posts:
                    break

                try:
                    post_data = self._parse_post(post)
                    posts.append(post_data)
                    count += 1

                    # Rate limiting 방지
                    if count % 10 == 0:
                        logger.debug(f"Collected {count}/{max_posts} posts")

                except Exception as e:
                    logger.warning(f"Error parsing post: {e}")
                    continue

            logger.info(f"Found {len(posts)} Instagram posts for #{clean_tag}")

        except instaloader.exceptions.InstaloaderException as e:
            logger.error(f"Instaloader error: {e}")
        except Exception as e:
            logger.error(f"Error searching Instagram hashtag: {e}")

        return posts

    def get_posts_by_location(
        self,
        location_id: int,
        max_posts: int = 50
    ) -> List[Dict]:
        """
        위치 태그로 포스트 검색

        Args:
            location_id: Instagram 위치 ID
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        posts = []

        try:
            # 위치로 포스트 가져오기
            location_posts = instaloader.NodeIterator(
                self.loader.context,
                f"locations/{location_id}/",
                lambda d: d['location']['edge_location_to_media'],
                lambda n: instaloader.Post(self.loader.context, n)
            )

            count = 0
            for post in location_posts:
                if count >= max_posts:
                    break

                try:
                    post_data = self._parse_post(post)
                    posts.append(post_data)
                    count += 1

                except Exception as e:
                    logger.warning(f"Error parsing post: {e}")
                    continue

            logger.info(f"Found {len(posts)} Instagram posts for location {location_id}")

        except Exception as e:
            logger.error(f"Error searching by location: {e}")

        return posts

    def get_profile_posts(
        self,
        username: str,
        max_posts: int = 50
    ) -> List[Dict]:
        """
        특정 사용자의 포스트 가져오기

        Args:
            username: Instagram 사용자명
            max_posts: 최대 수집 포스트 수

        Returns:
            포스트 정보 리스트
        """
        posts = []

        try:
            # 프로필 가져오기
            profile = instaloader.Profile.from_username(
                self.loader.context,
                username
            )

            count = 0
            for post in profile.get_posts():
                if count >= max_posts:
                    break

                try:
                    post_data = self._parse_post(post)
                    posts.append(post_data)
                    count += 1

                except Exception as e:
                    logger.warning(f"Error parsing post: {e}")
                    continue

            logger.info(f"Found {len(posts)} Instagram posts for @{username}")

        except instaloader.exceptions.ProfileNotExistsException:
            logger.error(f"Profile not found: {username}")
        except Exception as e:
            logger.error(f"Error getting profile posts: {e}")

        return posts

    def _parse_post(self, post: instaloader.Post) -> Dict:
        """
        Post 객체를 파싱하여 구조화된 데이터로 변환

        Args:
            post: Instaloader Post 객체

        Returns:
            파싱된 포스트 데이터
        """
        # 해시태그 추출
        hashtags = []
        if post.caption_hashtags:
            hashtags = list(post.caption_hashtags)

        # 미디어 타입 결정
        if post.is_video:
            media_type = 'video'
        elif post.typename == 'GraphSidecar':
            media_type = 'carousel'
        else:
            media_type = 'photo'

        # URL 생성
        post_url = f"https://www.instagram.com/p/{post.shortcode}/"

        return {
            'shortcode': post.shortcode,
            'owner_username': post.owner_username,
            'owner_id': str(post.owner_id),
            'caption': post.caption if post.caption else "",
            'hashtags': ','.join(hashtags) if hashtags else None,
            'post_url': post_url,
            'media_type': media_type,
            'media_url': post.url,
            'posted_at': post.date_utc,
            # 메트릭
            'like_count': post.likes,
            'comment_count': post.comments,
            'video_view_count': post.video_view_count if post.is_video else None,
        }


# 유틸리티 함수
def create_scraper_with_login() -> InstagramScraper:
    """
    환경 변수에서 로그인 정보를 읽어 스크래퍼 생성

    Returns:
        InstagramScraper 인스턴스
    """
    username = os.getenv("INSTAGRAM_USERNAME")
    password = os.getenv("INSTAGRAM_PASSWORD")

    return InstagramScraper(username=username, password=password)


def search_multiple_hashtags(hashtags: List[str], max_posts_per_tag: int = 50) -> Dict[str, List[Dict]]:
    """
    여러 해시태그 동시 검색

    Args:
        hashtags: 해시태그 리스트
        max_posts_per_tag: 태그당 최대 포스트 수

    Returns:
        {hashtag: [posts]} 형식의 딕셔너리
    """
    scraper = create_scraper_with_login()
    results = {}

    for tag in hashtags:
        try:
            posts = scraper.search_hashtag(tag, max_posts=max_posts_per_tag)
            results[tag] = posts
        except Exception as e:
            logger.error(f"Error searching hashtag {tag}: {e}")
            results[tag] = []

    return results
