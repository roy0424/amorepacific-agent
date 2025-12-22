"""
Prefect Tasks for social media scraping
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import os

from dotenv import load_dotenv
from prefect import task
from loguru import logger

from src.scrapers.social.youtube import YouTubeScraper
from src.scrapers.social.tiktok import TikTokScraper
from src.scrapers.social.instagram import InstagramScraper

# Load environment variables
load_dotenv()


# ===========================
# YouTube Tasks
# ===========================

@task(
    name="scrape-youtube-videos",
    description="Scrape YouTube videos by search query",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
def scrape_youtube_videos_task(
    query: str,
    max_results: int = 50,
    published_after: Optional[datetime] = None
) -> List[Dict[str, Any]]:
    """
    Search YouTube videos by query

    Args:
        query: Search query (e.g., 'laneige')
        max_results: Maximum number of videos
        published_after: Filter videos published after this date

    Returns:
        List of video data dictionaries
    """
    logger.info(f"Task: Scraping YouTube videos - query='{query}', max={max_results}")

    try:
        scraper = YouTubeScraper()
        videos = scraper.search_videos(
            query=query,
            max_results=max_results,
            published_after=published_after
        )

        logger.info(f"Task complete: Scraped {len(videos)} YouTube videos")
        return videos

    except Exception as e:
        logger.error(f"Task failed: Error scraping YouTube: {e}")
        raise


@task(
    name="scrape-youtube-hashtag",
    description="Scrape YouTube videos by hashtag",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
def scrape_youtube_hashtag_task(
    hashtag: str,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    Search YouTube videos by hashtag

    Args:
        hashtag: Hashtag (with or without #)
        max_results: Maximum number of videos

    Returns:
        List of video data dictionaries
    """
    logger.info(f"Task: Scraping YouTube hashtag - #{hashtag}, max={max_results}")

    try:
        scraper = YouTubeScraper()
        videos = scraper.search_by_hashtag(hashtag=hashtag, max_results=max_results)

        logger.info(f"Task complete: Scraped {len(videos)} videos for #{hashtag}")
        return videos

    except Exception as e:
        logger.error(f"Task failed: Error scraping YouTube hashtag: {e}")
        raise


@task(
    name="scrape-youtube-comments",
    description="Scrape comments for YouTube videos",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=600,
    log_prints=True
)
def scrape_youtube_comments_task(
    video_ids: List[str],
    max_comments_per_video: int = 50
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape comments for multiple YouTube videos

    Args:
        video_ids: List of YouTube video IDs
        max_comments_per_video: Max comments to collect per video

    Returns:
        Dictionary mapping video_id to list of comments
    """
    logger.info(f"Task: Scraping comments for {len(video_ids)} videos")

    try:
        scraper = YouTubeScraper()
        all_comments = {}

        for video_id in video_ids:
            comments = scraper.get_video_comments(video_id, max_results=max_comments_per_video)
            all_comments[video_id] = comments

        total_comments = sum(len(comments) for comments in all_comments.values())
        logger.info(f"Task complete: Scraped {total_comments} total comments")

        return all_comments

    except Exception as e:
        logger.error(f"Task failed: Error scraping YouTube comments: {e}")
        raise


@task(
    name="scrape-youtube-captions",
    description="Scrape captions for YouTube videos",
    retries=2,
    retry_delay_seconds=30,
    timeout_seconds=600,
    log_prints=True
)
def scrape_youtube_captions_task(
    video_ids: List[str],
    languages: List[str] = ['en', 'ko']
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape captions for multiple YouTube videos

    Args:
        video_ids: List of YouTube video IDs
        languages: Preferred languages

    Returns:
        Dictionary mapping video_id to list of captions
    """
    logger.info(f"Task: Scraping captions for {len(video_ids)} videos")

    try:
        scraper = YouTubeScraper()
        all_captions = {}

        for video_id in video_ids:
            captions = scraper.get_video_captions(video_id, languages=languages)
            all_captions[video_id] = captions

        total_captions = sum(len(captions) for captions in all_captions.values())
        logger.info(f"Task complete: Scraped {total_captions} total captions")

        return all_captions

    except Exception as e:
        logger.error(f"Task failed: Error scraping YouTube captions: {e}")
        raise


# ===========================
# TikTok Tasks
# ===========================

@task(
    name="scrape-tiktok-hashtag",
    description="Scrape TikTok videos by hashtag",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
async def scrape_tiktok_hashtag_task(
    hashtag: str,
    max_videos: int = 30,
    scroll_count: int = 3
) -> List[Dict[str, Any]]:
    """
    Search TikTok videos by hashtag

    자동으로 사용 가능한 API를 감지하여 사용 (우선순위 순서):
    1. Apify clockworks/tiktok-scraper (가장 안정적, 권장) ⭐
    2. Oxylabs Scraper API
    3. TikTok Research API (연구자 전용)
    4. Playwright 웹 스크래핑 (폴백)

    Args:
        hashtag: Hashtag (with or without #)
        max_videos: Maximum number of videos
        scroll_count: Number of scrolls to load more videos (Playwright only)

    Returns:
        List of video data dictionaries
    """
    logger.info(f"Task: Scraping TikTok hashtag - #{hashtag}, max={max_videos}")

    # 우선순위 1: Apify clockworks/tiktok-scraper (가장 안정적)
    apify_api_key = os.getenv("APIFY_API_KEY")

    if apify_api_key:
        try:
            logger.info("✅ Using Apify TikTok Scraper (clockworks/tiktok-scraper)")
            from src.scrapers.social.tiktok_apify import TikTokApify

            scraper = TikTokApify()
            videos = scraper.search_hashtag(
                hashtag=hashtag,
                max_videos=max_videos
            )
            logger.info(f"Task complete: Scraped {len(videos)} TikTok videos via Apify")
            return videos

        except Exception as e:
            logger.warning(f"Apify failed, trying fallback: {e}")

    # 우선순위 2: Oxylabs Scraper API
    oxylabs_username = os.getenv("OXYLABS_USERNAME")
    oxylabs_password = os.getenv("OXYLABS_PASSWORD")

    if oxylabs_username and oxylabs_password:
        try:
            logger.info("✅ Using Oxylabs TikTok Scraper API")
            from src.scrapers.social.tiktok_oxylabs import TikTokOxylabs

            scraper = TikTokOxylabs()
            videos = scraper.search_hashtag(
                hashtag=hashtag,
                max_videos=max_videos
            )
            logger.info(f"Task complete: Scraped {len(videos)} TikTok videos via Oxylabs")
            return videos

        except Exception as e:
            logger.warning(f"Oxylabs failed, trying fallback: {e}")

    # 우선순위 3: TikTok Research API
    tiktok_client_key = os.getenv("TIKTOK_CLIENT_KEY")
    tiktok_client_secret = os.getenv("TIKTOK_CLIENT_SECRET")

    if tiktok_client_key and tiktok_client_secret:
        try:
            logger.info("✅ Using TikTok Research API")
            from src.scrapers.social.tiktok_api import TikTokResearchAPI

            api = TikTokResearchAPI()
            videos = api.search_videos_by_hashtag(
                hashtag=hashtag,
                max_count=max_videos,
                days_back=30
            )
            logger.info(f"Task complete: Scraped {len(videos)} TikTok videos via Research API")
            return videos

        except Exception as e:
            logger.warning(f"Research API failed, trying fallback: {e}")

    # 우선순위 4: Playwright 웹 스크래핑 (폴백)
    logger.warning("⚠️  No API credentials found. Using Playwright web scraping (limited)")
    try:
        async with TikTokScraper(headless=True) as scraper:
            videos = await scraper.search_hashtag(
                hashtag=hashtag,
                max_videos=max_videos,
                scroll_count=scroll_count
            )

        logger.info(f"Task complete: Scraped {len(videos)} TikTok videos via Playwright")
        return videos

    except Exception as e:
        logger.error(f"Task failed: All TikTok scraping methods failed: {e}")
        raise


# ===========================
# Instagram Tasks
# ===========================

@task(
    name="scrape-instagram-hashtag",
    description="Scrape Instagram posts by hashtag",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
def scrape_instagram_hashtag_task(
    hashtag: str,
    max_posts: int = 50
) -> List[Dict[str, Any]]:
    """
    Search Instagram posts by hashtag

    자동으로 사용 가능한 API를 감지하여 사용 (우선순위 순서):
    1. Apify instagram-scraper (가장 안정적, 권장) ⭐
    2. Instaloader 웹 스크래핑 (폴백)

    Args:
        hashtag: Hashtag (with or without #)
        max_posts: Maximum number of posts

    Returns:
        List of post data dictionaries
    """
    logger.info(f"Task: Scraping Instagram hashtag - #{hashtag}, max={max_posts}")

    # 우선순위 1: Apify instagram-scraper (가장 안정적)
    apify_api_key = os.getenv("APIFY_API_KEY")

    if apify_api_key:
        try:
            logger.info("✅ Using Apify Instagram Scraper")
            from src.scrapers.social.instagram_apify import InstagramApify

            scraper = InstagramApify()
            posts = scraper.search_hashtag(
                hashtag=hashtag,
                max_posts=max_posts
            )
            logger.info(f"Task complete: Scraped {len(posts)} Instagram posts via Apify")
            return posts

        except Exception as e:
            logger.warning(f"Apify failed, trying fallback: {e}")

    # 우선순위 2: Instaloader (폴백)
    logger.warning("⚠️  No Apify API key found. Using Instaloader (slower, may be rate-limited)")
    try:
        from src.scrapers.social.instagram import create_scraper_with_login

        # 환경변수에서 로그인 정보를 자동으로 읽음
        scraper = create_scraper_with_login()
        posts = scraper.search_hashtag(hashtag=hashtag, max_posts=max_posts)

        logger.info(f"Task complete: Scraped {len(posts)} Instagram posts via Instaloader")
        return posts

    except Exception as e:
        logger.error(f"Task failed: All Instagram scraping methods failed: {e}")
        raise


@task(
    name="scrape-instagram-profile",
    description="Scrape Instagram posts from a profile",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
def scrape_instagram_profile_task(
    username: str,
    max_posts: int = 50
) -> List[Dict[str, Any]]:
    """
    Get posts from an Instagram profile

    자동으로 사용 가능한 API를 감지하여 사용:
    1. Apify instagram-scraper (권장) ⭐
    2. Instaloader (폴백)

    Args:
        username: Instagram username
        max_posts: Maximum number of posts

    Returns:
        List of post data dictionaries
    """
    logger.info(f"Task: Scraping Instagram profile - @{username}, max={max_posts}")

    # 우선순위 1: Apify
    apify_api_key = os.getenv("APIFY_API_KEY")

    if apify_api_key:
        try:
            logger.info("✅ Using Apify Instagram Scraper")
            from src.scrapers.social.instagram_apify import InstagramApify

            scraper = InstagramApify()
            posts = scraper.search_profile(
                username=username,
                max_posts=max_posts
            )
            logger.info(f"Task complete: Scraped {len(posts)} posts from @{username} via Apify")
            return posts

        except Exception as e:
            logger.warning(f"Apify failed, trying fallback: {e}")

    # 우선순위 2: Instaloader
    logger.warning("⚠️  No Apify API key. Using Instaloader")
    try:
        from src.scrapers.social.instagram import create_scraper_with_login

        scraper = create_scraper_with_login()
        posts = scraper.get_profile_posts(username=username, max_posts=max_posts)

        logger.info(f"Task complete: Scraped {len(posts)} posts from @{username} via Instaloader")
        return posts

    except Exception as e:
        logger.error(f"Task failed: All Instagram scraping methods failed: {e}")
        raise


# ===========================
# Multi-Platform Tasks
# ===========================

@task(
    name="scrape-all-social-platforms",
    description="Scrape all social media platforms for a brand",
    retries=2,
    retry_delay_seconds=120,
    timeout_seconds=900,
    log_prints=True
)
async def scrape_all_social_platforms_task(
    brand_keywords: List[str],
    hashtags: List[str],
    max_items_per_platform: int = 50
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape all social media platforms (YouTube, TikTok, Instagram)

    Args:
        brand_keywords: Brand search keywords (e.g., ['laneige'])
        hashtags: Hashtags to search (e.g., ['laneige', 'laniegelipmask'])
        max_items_per_platform: Max items per platform

    Returns:
        Dictionary with platform results: {'youtube': [...], 'tiktok': [...], 'instagram': [...]}
    """
    logger.info(f"Task: Scraping all social platforms - keywords={brand_keywords}, hashtags={hashtags}")

    results = {
        'youtube': [],
        'tiktok': [],
        'instagram': []
    }

    # YouTube
    try:
        youtube_scraper = YouTubeScraper()
        for keyword in brand_keywords:
            videos = youtube_scraper.search_videos(query=keyword, max_results=max_items_per_platform)
            results['youtube'].extend(videos)
        logger.info(f"YouTube: Collected {len(results['youtube'])} videos")
    except Exception as e:
        logger.error(f"YouTube scraping failed: {e}")

    # TikTok - Apify 우선 사용
    try:
        apify_api_key_tiktok = os.getenv("APIFY_API_KEY")

        if apify_api_key_tiktok:
            # Apify 사용
            logger.info("Using Apify TikTok Scraper")
            from src.scrapers.social.tiktok_apify import TikTokApify
            tiktok_scraper = TikTokApify()
            for tag in hashtags:
                videos = tiktok_scraper.search_hashtag(hashtag=tag, max_videos=max_items_per_platform)
                results['tiktok'].extend(videos)
            logger.info(f"TikTok (Apify): Collected {len(results['tiktok'])} videos")
        else:
            # Playwright 폴백
            logger.warning("No Apify API key found. Using Playwright for TikTok (may fail)")
            async with TikTokScraper(headless=True) as tiktok_scraper:
                for tag in hashtags:
                    videos = await tiktok_scraper.search_hashtag(hashtag=tag, max_videos=max_items_per_platform)
                    results['tiktok'].extend(videos)
            logger.info(f"TikTok (Playwright): Collected {len(results['tiktok'])} videos")
    except Exception as e:
        logger.error(f"TikTok scraping failed: {e}")

    # Instagram - Apify 우선 사용
    try:
        apify_api_key = os.getenv("APIFY_API_KEY")

        if apify_api_key:
            # Apify 사용
            logger.info("Using Apify Instagram Scraper")
            from src.scrapers.social.instagram_apify import InstagramApify
            instagram_scraper = InstagramApify()
            for tag in hashtags:
                posts = instagram_scraper.search_hashtag(hashtag=tag, max_posts=max_items_per_platform)
                results['instagram'].extend(posts)
            logger.info(f"Instagram (Apify): Collected {len(results['instagram'])} posts")
        else:
            # Instaloader 폴백
            logger.warning("No Apify API key found. Using Instaloader (may fail)")
            from src.scrapers.social.instagram import create_scraper_with_login
            instagram_scraper = create_scraper_with_login()
            for tag in hashtags:
                posts = instagram_scraper.search_hashtag(hashtag=tag, max_posts=max_items_per_platform)
                results['instagram'].extend(posts)
            logger.info(f"Instagram (Instaloader): Collected {len(results['instagram'])} posts")
    except Exception as e:
        logger.error(f"Instagram scraping failed: {e}")
        # Instagram 실패해도 다른 플랫폼은 계속 진행

    total_items = sum(len(items) for items in results.values())
    logger.info(f"Task complete: Scraped {total_items} total items across all platforms")

    return results
