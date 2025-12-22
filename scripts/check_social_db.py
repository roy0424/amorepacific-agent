#!/usr/bin/env python3
"""
Check social media data in database
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
from loguru import logger

from config.settings import settings
from src.models.social_media import (
    YouTubeVideo,
    TikTokPost,
    InstagramPost
)


def check_social_data():
    """Check recent social media data in database"""

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        logger.info("=" * 80)
        logger.info("Checking Social Media Data in Database")
        logger.info("=" * 80)

        # Get data from last 24 hours
        cutoff_time = datetime.now() - timedelta(hours=24)

        # YouTube
        youtube_count = session.query(YouTubeVideo).filter(
            YouTubeVideo.last_collected_at >= cutoff_time
        ).count()

        youtube_total = session.query(YouTubeVideo).count()

        latest_youtube = session.query(YouTubeVideo).order_by(
            YouTubeVideo.last_collected_at.desc()
        ).first()

        logger.info(f"\n📺 YouTube Videos:")
        logger.info(f"  Total in DB: {youtube_total}")
        logger.info(f"  Last 24h: {youtube_count}")
        if latest_youtube:
            logger.info(f"  Latest: {latest_youtube.title[:50]}...")
            logger.info(f"  Channel: {latest_youtube.channel_title}")
            # Get latest metrics
            if latest_youtube.metrics:
                latest_metric = sorted(latest_youtube.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                logger.info(f"  Views: {latest_metric.view_count:,}")
            logger.info(f"  Collected: {latest_youtube.last_collected_at}")

        # TikTok
        tiktok_count = session.query(TikTokPost).filter(
            TikTokPost.last_collected_at >= cutoff_time
        ).count()

        tiktok_total = session.query(TikTokPost).count()

        latest_tiktok = session.query(TikTokPost).order_by(
            TikTokPost.last_collected_at.desc()
        ).first()

        logger.info(f"\n🎵 TikTok Videos:")
        logger.info(f"  Total in DB: {tiktok_total}")
        logger.info(f"  Last 24h: {tiktok_count}")
        if latest_tiktok:
            logger.info(f"  Latest: {latest_tiktok.description[:50] if latest_tiktok.description else 'No description'}...")
            logger.info(f"  Author: @{latest_tiktok.author_username}")
            # Get latest metrics for this post
            if latest_tiktok.metrics:
                latest_metric = sorted(latest_tiktok.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                logger.info(f"  Views: {latest_metric.view_count:,}")
                logger.info(f"  Likes: {latest_metric.like_count:,}")
            logger.info(f"  Collected: {latest_tiktok.last_collected_at}")

        # Instagram
        instagram_count = session.query(InstagramPost).filter(
            InstagramPost.last_collected_at >= cutoff_time
        ).count()

        instagram_total = session.query(InstagramPost).count()

        latest_instagram = session.query(InstagramPost).order_by(
            InstagramPost.last_collected_at.desc()
        ).first()

        logger.info(f"\n📸 Instagram Posts:")
        logger.info(f"  Total in DB: {instagram_total}")
        logger.info(f"  Last 24h: {instagram_count}")
        if latest_instagram:
            logger.info(f"  Latest: {latest_instagram.caption[:50] if latest_instagram.caption else 'No caption'}...")
            logger.info(f"  Owner: @{latest_instagram.owner_username}")
            # Get latest metrics
            if latest_instagram.metrics:
                latest_metric = sorted(latest_instagram.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                logger.info(f"  Likes: {latest_metric.like_count:,}")
                logger.info(f"  Comments: {latest_metric.comment_count:,}")
            logger.info(f"  Collected: {latest_instagram.last_collected_at}")

        # Summary
        logger.info("\n" + "=" * 80)
        logger.info("Summary:")
        logger.info("=" * 80)
        logger.info(f"Total items in DB: {youtube_total + tiktok_total + instagram_total}")
        logger.info(f"  YouTube: {youtube_total}")
        logger.info(f"  TikTok: {tiktok_total}")
        logger.info(f"  Instagram: {instagram_total}")
        logger.info(f"\nLast 24h: {youtube_count + tiktok_count + instagram_count}")
        logger.info(f"  YouTube: {youtube_count}")
        logger.info(f"  TikTok: {tiktok_count}")
        logger.info(f"  Instagram: {instagram_count}")

        # Top hashtags
        logger.info("\n" + "=" * 80)
        logger.info("Recent Activity:")
        logger.info("=" * 80)

        # Recent YouTube videos
        recent_youtube = session.query(YouTubeVideo).filter(
            YouTubeVideo.last_collected_at >= cutoff_time
        ).order_by(YouTubeVideo.last_collected_at.desc()).limit(5).all()

        if recent_youtube:
            logger.info("\n📺 Recent YouTube Videos:")
            for i, video in enumerate(recent_youtube, 1):
                logger.info(f"  {i}. {video.title[:60]}")
                metrics_str = ""
                if video.metrics:
                    latest_metric = sorted(video.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                    metrics_str = f" | Views: {latest_metric.view_count:,}"
                logger.info(f"     Channel: {video.channel_title}{metrics_str} | {video.last_collected_at}")

        # Recent TikTok videos
        recent_tiktok = session.query(TikTokPost).filter(
            TikTokPost.last_collected_at >= cutoff_time
        ).order_by(TikTokPost.last_collected_at.desc()).limit(5).all()

        if recent_tiktok:
            logger.info("\n🎵 Recent TikTok Videos:")
            for i, video in enumerate(recent_tiktok, 1):
                desc = video.description[:60] if video.description else "No description"
                logger.info(f"  {i}. {desc}")
                metrics_str = ""
                if video.metrics:
                    latest_metric = sorted(video.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                    metrics_str = f" | Views: {latest_metric.view_count:,} | Likes: {latest_metric.like_count:,}"
                logger.info(f"     @{video.author_username}{metrics_str} | {video.last_collected_at}")

        # Recent Instagram posts
        recent_instagram = session.query(InstagramPost).filter(
            InstagramPost.last_collected_at >= cutoff_time
        ).order_by(InstagramPost.last_collected_at.desc()).limit(5).all()

        if recent_instagram:
            logger.info("\n📸 Recent Instagram Posts:")
            for i, post in enumerate(recent_instagram, 1):
                caption = post.caption[:60] if post.caption else "No caption"
                logger.info(f"  {i}. {caption}")
                metrics_str = ""
                if post.metrics:
                    latest_metric = sorted(post.metrics, key=lambda m: m.collected_at, reverse=True)[0]
                    metrics_str = f" | Likes: {latest_metric.like_count:,} | Comments: {latest_metric.comment_count:,}"
                logger.info(f"     @{post.owner_username}{metrics_str} | {post.last_collected_at}")

    except Exception as e:
        logger.error(f"Error checking database: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    check_social_data()
