#!/usr/bin/env python3
"""
Instagram US Market Collection Script
미국 시장 타겟 Instagram 데이터 수집 스크립트
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
from src.scrapers.social.instagram_apify import InstagramApify
from config.instagram_strategy_us import (
    DAILY_CONFIG,
    WEEKLY_CONFIG,
    MONTHLY_CONFIG,
    INFLUENCER_CONFIG,
    BUDGET_CONFIG,
)


def collect_daily(scraper: InstagramApify):
    """Daily collection for trend monitoring"""
    logger.info("=" * 60)
    logger.info("Starting DAILY Instagram collection (US Market)")
    logger.info("=" * 60)

    all_posts = []
    config = DAILY_CONFIG

    for hashtag in config["hashtags"]:
        try:
            logger.info(f"Collecting: #{hashtag}")

            posts = scraper.search_hashtag(
                hashtag=hashtag,
                max_posts=config["max_posts_per_hashtag"],
            )

            logger.info(f"  ✓ Collected {len(posts)} posts from #{hashtag}")
            all_posts.extend(posts)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect #{hashtag}: {e}")
            continue

    logger.success(f"Daily collection complete: {len(all_posts)} total posts")
    return all_posts


def collect_weekly(scraper: InstagramApify):
    """Weekly collection for detailed analysis"""
    logger.info("=" * 60)
    logger.info("Starting WEEKLY Instagram collection (US Market)")
    logger.info("=" * 60)

    all_posts = []
    config = WEEKLY_CONFIG

    for hashtag in config["hashtags"]:
        try:
            logger.info(f"Collecting: #{hashtag}")

            posts = scraper.search_hashtag(
                hashtag=hashtag,
                max_posts=config["max_posts_per_hashtag"],
            )

            logger.info(f"  ✓ Collected {len(posts)} posts from #{hashtag}")
            all_posts.extend(posts)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect #{hashtag}: {e}")
            continue

    logger.success(f"Weekly collection complete: {len(all_posts)} total posts")
    return all_posts


def collect_influencers(scraper: InstagramApify):
    """Monitor US influencers and official accounts"""
    logger.info("=" * 60)
    logger.info("Starting INFLUENCER monitoring (US Market)")
    logger.info("=" * 60)

    all_posts = []
    config = INFLUENCER_CONFIG

    for profile in config["profiles"]:
        try:
            logger.info(f"Collecting: @{profile}")

            posts = scraper.search_profile(
                username=profile,
                max_posts=config["max_posts_per_profile"],
            )

            logger.info(f"  ✓ Collected {len(posts)} posts from @{profile}")
            all_posts.extend(posts)

        except Exception as e:
            logger.error(f"  ✗ Failed to collect @{profile}: {e}")
            continue

    logger.success(f"Influencer monitoring complete: {len(all_posts)} total posts")
    return all_posts


def save_to_database(posts: list):
    """Save collected posts to database"""
    from src.database.session import get_session
    from src.models.social_media import InstagramPost
    from src.services.social_service import InstagramService

    logger.info(f"Saving {len(posts)} posts to database...")

    try:
        with get_session() as session:
            service = InstagramService(session)
            stats = service.save_posts(posts)

            logger.success("Database save complete:")
            logger.info(f"  - Posts created: {stats.get('posts_created', 0)}")
            logger.info(f"  - Posts updated: {stats.get('posts_updated', 0)}")
            logger.info(f"  - Metrics created: {stats.get('metrics_created', 0)}")

            return stats

    except Exception as e:
        logger.error(f"Failed to save to database: {e}")
        raise


def estimate_cost(total_posts: int):
    """Estimate Apify cost"""
    cost_per_1000 = BUDGET_CONFIG["cost_per_1000_posts"]
    estimated_cost = (total_posts / 1000) * cost_per_1000

    logger.info("=" * 60)
    logger.info("Cost Estimation:")
    logger.info(f"  - Total posts: {total_posts}")
    logger.info(f"  - Estimated cost: ${estimated_cost:.2f}")
    logger.info(f"  - Cost per 1000: ${cost_per_1000:.2f}")
    logger.info(f"  - Monthly quota: {BUDGET_CONFIG['max_posts_per_month']}")
    logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Instagram US Market Collection")
    parser.add_argument(
        "--mode",
        choices=["daily", "weekly", "monthly", "influencer", "all"],
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
    logger.info("Initializing Apify Instagram Scraper...")
    scraper = InstagramApify()

    all_posts = []

    try:
        if args.mode == "daily" or args.mode == "all":
            posts = collect_daily(scraper)
            all_posts.extend(posts)

        if args.mode == "weekly" or args.mode == "all":
            posts = collect_weekly(scraper)
            all_posts.extend(posts)

        if args.mode == "influencer" or args.mode == "all":
            posts = collect_influencers(scraper)
            all_posts.extend(posts)

        # Remove duplicates
        unique_posts = []
        seen_ids = set()
        for post in all_posts:
            shortcode = post.get("shortcode")
            if shortcode and shortcode not in seen_ids:
                seen_ids.add(shortcode)
                unique_posts.append(post)

        logger.info(f"Total unique posts collected: {len(unique_posts)}")

        # Estimate cost
        estimate_cost(len(unique_posts))

        # Save to database (unless dry-run)
        if not args.dry_run:
            if unique_posts:
                save_to_database(unique_posts)
            else:
                logger.warning("No posts to save!")
        else:
            logger.info("DRY RUN - Skipping database save")

        logger.success("Collection completed successfully!")

    except Exception as e:
        logger.error(f"Collection failed: {e}")
        raise


if __name__ == "__main__":
    main()
