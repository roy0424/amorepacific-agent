#!/usr/bin/env python3
"""
TikTok US Market Collection Script
미국 시장 타겟 TikTok 데이터 수집 스크립트
"""
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import argparse

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv(project_root / ".env")

from loguru import logger
from src.scrapers.social.tiktok_apify import TikTokApify
from config.tiktok_strategy_us import (
    DAILY_CONFIG,
    WEEKLY_CONFIG,
    MONTHLY_CONFIG,
    INFLUENCER_CONFIG,
    SEARCH_KEYWORDS,
    BUDGET_CONFIG,
)


def collect_daily(scraper: TikTokApify):
    """Daily collection for trend monitoring"""
    logger.info("=" * 60)
    logger.info("Starting DAILY collection (US Market)")
    logger.info("=" * 60)

    all_videos = []
    config = DAILY_CONFIG

    for hashtag in config["hashtags"]:
        try:
            logger.info(f"Collecting: #{hashtag}")

            videos = scraper.search_hashtag(
                hashtag=hashtag,
                max_videos=config["max_videos_per_hashtag"],
                min_likes=config["min_likes"],
                date_from=datetime.now() - timedelta(days=config["date_range_days"]),
                date_to=datetime.now(),
            )

            logger.info(f"  ✓ Collected {len(videos)} videos from #{hashtag}")
            all_videos.extend(videos)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect #{hashtag}: {e}")
            continue

    logger.success(f"Daily collection complete: {len(all_videos)} total videos")
    return all_videos


def collect_weekly(scraper: TikTokApify):
    """Weekly collection for detailed analysis"""
    logger.info("=" * 60)
    logger.info("Starting WEEKLY collection (US Market)")
    logger.info("=" * 60)

    all_videos = []
    config = WEEKLY_CONFIG

    for hashtag in config["hashtags"]:
        try:
            logger.info(f"Collecting: #{hashtag}")

            videos = scraper.search_hashtag(
                hashtag=hashtag,
                max_videos=config["max_videos_per_hashtag"],
                min_likes=config["min_likes"],
                date_from=datetime.now() - timedelta(days=config["date_range_days"]),
                date_to=datetime.now(),
            )

            logger.info(f"  ✓ Collected {len(videos)} videos from #{hashtag}")
            all_videos.extend(videos)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect #{hashtag}: {e}")
            continue

    logger.success(f"Weekly collection complete: {len(all_videos)} total videos")
    return all_videos


def collect_influencers(scraper: TikTokApify):
    """Monitor US influencers and official accounts"""
    logger.info("=" * 60)
    logger.info("Starting INFLUENCER monitoring (US Market)")
    logger.info("=" * 60)

    all_videos = []
    config = INFLUENCER_CONFIG

    for profile in config["profiles"]:
        try:
            logger.info(f"Collecting: @{profile}")

            videos = scraper.search_profile(
                username=profile,
                max_videos=config["max_videos_per_profile"],
            )

            logger.info(f"  ✓ Collected {len(videos)} videos from @{profile}")
            all_videos.extend(videos)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect @{profile}: {e}")
            continue

    logger.success(f"Influencer monitoring complete: {len(all_videos)} total videos")
    return all_videos


def collect_keywords(scraper: TikTokApify, max_per_keyword: int = 50):
    """Search by keywords"""
    logger.info("=" * 60)
    logger.info("Starting KEYWORD search (US Market)")
    logger.info("=" * 60)

    all_videos = []

    for keyword in SEARCH_KEYWORDS:
        try:
            logger.info(f"Searching: '{keyword}'")

            videos = scraper.search_keyword(
                keyword=keyword,
                max_videos=max_per_keyword,
            )

            logger.info(f"  ✓ Found {len(videos)} videos for '{keyword}'")
            all_videos.extend(videos)

        except Exception as e:
            logger.error(f"  ✗ Failed to search '{keyword}': {e}")
            continue

    logger.success(f"Keyword search complete: {len(all_videos)} total videos")
    return all_videos


def save_to_database(videos: list):
    """Save collected videos to database"""
    from src.database.session import get_session
    from src.models.social_media import TikTokVideo
    from src.services.social_service import TikTokService

    logger.info(f"Saving {len(videos)} videos to database...")

    try:
        with get_session() as session:
            service = TikTokService(session)
            stats = service.save_videos(videos)

            logger.success("Database save complete:")
            logger.info(f"  - Videos created: {stats.get('videos_created', 0)}")
            logger.info(f"  - Videos updated: {stats.get('videos_updated', 0)}")
            logger.info(f"  - Metrics created: {stats.get('metrics_created', 0)}")

            return stats

    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        raise


def estimate_cost(total_videos: int):
    """Estimate Apify cost"""
    cost_per_1000 = BUDGET_CONFIG["cost_per_1000_results"]
    estimated_cost = (total_videos / 1000) * cost_per_1000

    logger.info("=" * 60)
    logger.info("Cost Estimation:")
    logger.info(f"  - Total videos: {total_videos}")
    logger.info(f"  - Estimated cost: ${estimated_cost:.2f}")
    logger.info(f"  - Monthly budget: ${BUDGET_CONFIG['monthly_apify_budget']:.2f}")
    logger.info(f"  - Remaining budget: ${BUDGET_CONFIG['monthly_apify_budget'] - estimated_cost:.2f}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="TikTok US Market Collection")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly", "influencer", "keyword", "all"],
        default="daily",
        help="Collection mode",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what will be collected without actually collecting",
    )

    args = parser.parse_args()

    # Initialize scraper
    logger.info("Initializing Apify TikTok Scraper...")
    scraper = TikTokApify()

    all_videos = []

    try:
        if args.mode == "daily" or args.mode == "all":
            videos = collect_daily(scraper)
            all_videos.extend(videos)

        if args.mode == "weekly" or args.mode == "all":
            videos = collect_weekly(scraper)
            all_videos.extend(videos)

        if args.mode == "influencer" or args.mode == "all":
            videos = collect_influencers(scraper)
            all_videos.extend(videos)

        if args.mode == "keyword":
            videos = collect_keywords(scraper)
            all_videos.extend(videos)

        # Remove duplicates
        unique_videos = []
        seen_ids = set()
        for video in all_videos:
            vid_id = video.get("video_id")
            if vid_id and vid_id not in seen_ids:
                seen_ids.add(vid_id)
                unique_videos.append(video)

        logger.info(f"Total unique videos collected: {len(unique_videos)}")

        # Estimate cost
        estimate_cost(len(unique_videos))

        # Save to database (unless dry-run)
        if not args.dry_run:
            if unique_videos:
                save_to_database(unique_videos)
            else:
                logger.warning("No videos to save!")
        else:
            logger.info("DRY RUN - Skipping database save")

        logger.success("Collection completed successfully!")

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise


if __name__ == "__main__":
    main()
