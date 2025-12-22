#!/usr/bin/env python3
"""
ML Dataset Exporter - DB의 전체 소셜미디어 데이터를 AI 학습용 CSV로 변환
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import argparse
from datetime import datetime, timedelta
import pandas as pd
from loguru import logger
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from config.settings import settings
from src.models.social_media import (
    YouTubeVideo, YouTubeMetric,
    TikTokPost, TikTokMetric,
    InstagramPost, InstagramMetric
)


def export_ml_dataset(
    days: int = None,
    output_dir: str = "data/datasets",
    min_engagement: int = 0
):
    """
    DB에서 소셜미디어 데이터를 가져와 AI 학습용 CSV로 변환

    Args:
        days: 최근 N일 데이터만 (None이면 전체)
        output_dir: 출력 디렉토리
        min_engagement: 최소 engagement score 필터
    """
    logger.info("=" * 80)
    logger.info("ML Dataset Export - From Database")
    logger.info("=" * 80)

    # DB 연결
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        ml_dataset = []

        # 날짜 필터
        cutoff_date = None
        if days:
            cutoff_date = datetime.now() - timedelta(days=days)
            logger.info(f"Filtering data from last {days} days")

        # 1. YouTube 데이터
        logger.info("Extracting YouTube data...")
        youtube_query = select(YouTubeVideo, YouTubeMetric).join(
            YouTubeMetric,
            YouTubeVideo.id == YouTubeMetric.video_id
        ).order_by(YouTubeMetric.collected_at.desc())

        if cutoff_date:
            youtube_query = youtube_query.where(YouTubeVideo.last_collected_at >= cutoff_date)

        youtube_results = session.execute(youtube_query).all()

        # YouTube 비디오별로 최신 메트릭만 사용
        youtube_videos = {}
        for video, metric in youtube_results:
            if video.video_id not in youtube_videos:
                engagement_score = (
                    metric.like_count +
                    metric.comment_count * 2
                )

                if engagement_score >= min_engagement:
                    youtube_videos[video.video_id] = {
                        'platform': 'youtube',
                        'content_id': video.video_id,
                        'author': video.channel_title or '',
                        'text': f"{video.title or ''} {video.description or ''}",
                        'title': video.title or '',
                        'description': video.description or '',
                        'hashtags': video.tags or '',
                        'view_count': metric.view_count or 0,
                        'like_count': metric.like_count or 0,
                        'comment_count': metric.comment_count or 0,
                        'engagement_score': engagement_score,
                        'posted_at': video.published_at.isoformat() if video.published_at else '',
                        'url': video.video_url or '',
                        'duration_seconds': video.duration_seconds or 0,
                    }

        ml_dataset.extend(youtube_videos.values())
        logger.info(f"  Added {len(youtube_videos)} YouTube videos")

        # 2. TikTok 데이터
        logger.info("Extracting TikTok data...")
        tiktok_query = select(TikTokPost, TikTokMetric).join(
            TikTokMetric,
            TikTokPost.id == TikTokMetric.post_id
        ).order_by(TikTokMetric.collected_at.desc())

        if cutoff_date:
            tiktok_query = tiktok_query.where(TikTokPost.last_collected_at >= cutoff_date)

        tiktok_results = session.execute(tiktok_query).all()

        # TikTok 비디오별로 최신 메트릭만 사용
        tiktok_videos = {}
        for post, metric in tiktok_results:
            if post.video_id not in tiktok_videos:
                engagement_score = (
                    metric.like_count +
                    metric.comment_count * 2 +
                    (metric.share_count or 0) * 3
                )

                if engagement_score >= min_engagement:
                    tiktok_videos[post.video_id] = {
                        'platform': 'tiktok',
                        'content_id': post.video_id,
                        'author': post.author_username or '',
                        'text': post.description or '',
                        'title': '',
                        'description': post.description or '',
                        'hashtags': post.hashtags or '',
                        'view_count': metric.view_count or 0,
                        'like_count': metric.like_count or 0,
                        'comment_count': metric.comment_count or 0,
                        'engagement_score': engagement_score,
                        'posted_at': post.posted_at.isoformat() if post.posted_at else '',
                        'url': post.video_url or '',
                        'duration_seconds': post.duration_seconds or 0,
                    }

        ml_dataset.extend(tiktok_videos.values())
        logger.info(f"  Added {len(tiktok_videos)} TikTok videos")

        # 3. Instagram 데이터
        logger.info("Extracting Instagram data...")
        instagram_query = select(InstagramPost, InstagramMetric).join(
            InstagramMetric,
            InstagramPost.id == InstagramMetric.post_id
        ).order_by(InstagramMetric.collected_at.desc())

        if cutoff_date:
            instagram_query = instagram_query.where(InstagramPost.last_collected_at >= cutoff_date)

        instagram_results = session.execute(instagram_query).all()

        # Instagram 포스트별로 최신 메트릭만 사용
        instagram_posts = {}
        for post, metric in instagram_results:
            if post.shortcode not in instagram_posts:
                engagement_score = (
                    metric.like_count +
                    metric.comment_count * 2
                )

                if engagement_score >= min_engagement:
                    instagram_posts[post.shortcode] = {
                        'platform': 'instagram',
                        'content_id': post.shortcode,
                        'author': post.owner_username or '',
                        'text': post.caption or '',
                        'title': '',
                        'description': post.caption or '',
                        'hashtags': post.hashtags or '',
                        'view_count': metric.video_view_count or 0,
                        'like_count': metric.like_count or 0,
                        'comment_count': metric.comment_count or 0,
                        'engagement_score': engagement_score,
                        'posted_at': post.posted_at.isoformat() if post.posted_at else '',
                        'url': post.post_url or '',
                        'duration_seconds': 0,
                    }

        ml_dataset.extend(instagram_posts.values())
        logger.info(f"  Added {len(instagram_posts)} Instagram posts")

        # DataFrame 생성
        if not ml_dataset:
            logger.warning("No data found!")
            return None

        df = pd.DataFrame(ml_dataset)

        # 출력 디렉토리 생성
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # 파일명 생성
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"social_media_ml_dataset_{timestamp}.csv"
        csv_path = output_path / csv_filename

        # CSV 저장
        df.to_csv(csv_path, index=False, encoding='utf-8')

        # 통계 출력
        logger.info("=" * 80)
        logger.success(f"✅ ML Dataset Created: {csv_path}")
        logger.info("=" * 80)
        logger.info(f"Total Records: {len(ml_dataset):,}")
        logger.info(f"File Size: {csv_path.stat().st_size / 1024:.1f} KB")
        logger.info("")
        logger.info("Platform Distribution:")
        for platform, count in df['platform'].value_counts().items():
            logger.info(f"  {platform}: {count}")
        logger.info("")
        logger.info("Top 5 by Engagement:")
        top5 = df.nlargest(5, 'engagement_score')[['platform', 'author', 'engagement_score', 'like_count']]
        for idx, row in top5.iterrows():
            logger.info(f"  {row['platform']:10s} @{row['author']:20s} - Score: {row['engagement_score']:,}")
        logger.info("")
        logger.info(f"Engagement Stats:")
        logger.info(f"  Min: {df['engagement_score'].min():,}")
        logger.info(f"  Max: {df['engagement_score'].max():,}")
        logger.info(f"  Mean: {df['engagement_score'].mean():.0f}")
        logger.info(f"  Median: {df['engagement_score'].median():.0f}")
        logger.info("=" * 80)

        return csv_path

    except Exception as e:
        logger.error(f"Error creating ML dataset: {e}")
        import traceback
        traceback.print_exc()
        return None

    finally:
        session.close()


def main():
    parser = argparse.ArgumentParser(
        description="Export social media data as ML training dataset CSV"
    )
    parser.add_argument(
        '--days',
        type=int,
        default=None,
        help='최근 N일 데이터만 export (기본: 전체)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default='data/datasets',
        help='출력 디렉토리 (기본: data/datasets)'
    )
    parser.add_argument(
        '--min-engagement',
        type=int,
        default=0,
        help='최소 engagement score 필터 (기본: 0)'
    )

    args = parser.parse_args()

    export_ml_dataset(
        days=args.days,
        output_dir=args.output_dir,
        min_engagement=args.min_engagement
    )


if __name__ == "__main__":
    main()
