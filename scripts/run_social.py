#!/usr/bin/env python3
"""
Manual execution script for social media scraping flows
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

from loguru import logger

# Import flows
from src.flows.social_flow import (
    social_pipeline,
    social_test_pipeline,
    youtube_flow,
    tiktok_flow,
    instagram_flow
)


def setup_logging():
    """Setup logging configuration"""
    logger.remove()
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
        level="INFO"
    )


async def run_full_pipeline(keywords: list, hashtags: list, max_items: int):
    """Run the full social media pipeline"""
    logger.info("Running FULL social media pipeline")
    result = await social_pipeline(
        brand_keywords=keywords,
        hashtags=hashtags,
        max_items_per_platform=max_items
    )
    logger.info(f"Pipeline result: {result}")
    return result


async def run_test_pipeline():
    """Run the test pipeline (limited items)"""
    logger.info("Running TEST social media pipeline (10 items per platform)")
    result = await social_test_pipeline()
    logger.info(f"Pipeline result: {result}")
    return result


def run_youtube_only(query: str, max_results: int):
    """Run YouTube-only flow"""
    logger.info(f"Running YouTube-only flow: query='{query}', max={max_results}")
    result = youtube_flow(query=query, max_results=max_results)
    logger.info(f"YouTube flow result: {result}")
    return result


async def run_tiktok_only(hashtag: str, max_videos: int):
    """Run TikTok-only flow"""
    logger.info(f"Running TikTok-only flow: hashtag='{hashtag}', max={max_videos}")
    result = await tiktok_flow(hashtag=hashtag, max_videos=max_videos)
    logger.info(f"TikTok flow result: {result}")
    return result


def run_instagram_only(hashtag: str, max_posts: int):
    """Run Instagram-only flow"""
    logger.info(f"Running Instagram-only flow: hashtag='{hashtag}', max={max_posts}")
    result = instagram_flow(hashtag=hashtag, max_posts=max_posts)
    logger.info(f"Instagram flow result: {result}")
    return result


def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(
        description="Run social media scraping flows manually",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run test pipeline (10 items per platform)
  python scripts/run_social.py --flow social-test

  # Run full pipeline (50 items per platform)
  python scripts/run_social.py --flow social-full

  # Run YouTube only
  python scripts/run_social.py --flow youtube --query laneige --max 30

  # Run TikTok only
  python scripts/run_social.py --flow tiktok --hashtag laneige --max 20

  # Run Instagram only
  python scripts/run_social.py --flow instagram --hashtag laneige --max 30
        """
    )

    parser.add_argument(
        '--flow',
        type=str,
        required=True,
        choices=['social-full', 'social-test', 'youtube', 'tiktok', 'instagram'],
        help='Flow to run'
    )

    parser.add_argument(
        '--keywords',
        type=str,
        nargs='+',
        default=['laneige'],
        help='Brand keywords for full pipeline (space-separated)'
    )

    parser.add_argument(
        '--hashtags',
        type=str,
        nargs='+',
        default=['laneige', 'laniegelipmask'],
        help='Hashtags for full pipeline (space-separated)'
    )

    parser.add_argument(
        '--max',
        type=int,
        default=50,
        help='Maximum items to collect (default: 50)'
    )

    parser.add_argument(
        '--query',
        type=str,
        default='laneige',
        help='Search query for YouTube (default: laneige)'
    )

    parser.add_argument(
        '--hashtag',
        type=str,
        default='laneige',
        help='Hashtag for TikTok/Instagram (default: laneige)'
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging()

    try:
        if args.flow == 'social-full':
            asyncio.run(run_full_pipeline(args.keywords, args.hashtags, args.max))
        elif args.flow == 'social-test':
            asyncio.run(run_test_pipeline())
        elif args.flow == 'youtube':
            run_youtube_only(args.query, args.max)
        elif args.flow == 'tiktok':
            asyncio.run(run_tiktok_only(args.hashtag, args.max))
        elif args.flow == 'instagram':
            run_instagram_only(args.hashtag, args.max)

        logger.success("Execution completed successfully!")

    except KeyboardInterrupt:
        logger.warning("Execution interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
