"""
Social Media Scraping Flow - Complete pipeline for social media data collection
"""

from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path
import pandas as pd

from prefect import flow
from prefect.artifacts import create_markdown_artifact, create_table_artifact, create_link_artifact
from loguru import logger

from src.tasks.social_tasks import scrape_all_social_platforms_task
from src.tasks.processing_tasks import save_all_social_media_to_db_task


@flow(
    name="social-scraping-pipeline",
    description="Complete social media scraping and processing pipeline (YouTube, TikTok, Instagram)",
    log_prints=True,
    retries=1,
    retry_delay_seconds=300
)
async def social_pipeline(
    brand_keywords: List[str] = None,
    hashtags: List[str] = None,
    max_items_per_platform: int = 50
) -> Dict[str, Any]:
    """
    Complete social media scraping pipeline

    This flow:
    1. Scrapes all social media platforms (YouTube, TikTok, Instagram)
    2. Saves posts/videos and metrics to database
    3. Returns execution results

    Args:
        brand_keywords: Brand search keywords (default: ['laneige'])
        hashtags: Hashtags to search (default: ['laneige', 'laniegelipmask'])
        max_items_per_platform: Max items to collect per platform

    Returns:
        Dictionary with pipeline execution results
    """
    # Default values
    if brand_keywords is None:
        brand_keywords = ['laneige']
    if hashtags is None:
        hashtags = ['laneige', 'laniegelipmask', 'laneigesleepingmask']

    logger.info("=" * 80)
    logger.info("Starting Social Media Scraping Pipeline")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info(f"Keywords: {brand_keywords}")
    logger.info(f"Hashtags: {hashtags}")
    logger.info("=" * 80)

    pipeline_results = {
        'started_at': datetime.now(),
        'status': 'running',
        'scraping': {},
        'database': {}
    }

    try:
        # Step 1: Scrape all social platforms
        logger.info("Step 1/2: Scraping social media platforms...")
        social_data = await scrape_all_social_platforms_task(
            brand_keywords=brand_keywords,
            hashtags=hashtags,
            max_items_per_platform=max_items_per_platform
        )

        total_items = sum(len(items) for items in social_data.values())
        pipeline_results['scraping'] = {
            'youtube_videos': len(social_data.get('youtube', [])),
            'tiktok_videos': len(social_data.get('tiktok', [])),
            'instagram_posts': len(social_data.get('instagram', [])),
            'total_items': total_items,
            'status': 'success'
        }
        logger.info(f"Scraping complete: {total_items} total items collected")
        logger.info(f"  - YouTube: {len(social_data.get('youtube', []))} videos")
        logger.info(f"  - TikTok: {len(social_data.get('tiktok', []))} videos")
        logger.info(f"  - Instagram: {len(social_data.get('instagram', []))} posts")

        # Step 2: Save to database
        logger.info("Step 2/2: Saving to database...")
        db_stats = save_all_social_media_to_db_task(
            social_data=social_data,
            brand_name="Laneige"
        )
        pipeline_results['database'] = db_stats
        logger.info(f"Database save complete: {db_stats}")

        # Mark pipeline as successful
        pipeline_results['status'] = 'success'
        pipeline_results['completed_at'] = datetime.now()

        # Calculate duration
        duration = (pipeline_results['completed_at'] - pipeline_results['started_at']).total_seconds()
        pipeline_results['duration_seconds'] = duration

        logger.info("=" * 80)
        logger.info(f"Social Media Pipeline Complete - Duration: {duration:.1f}s")
        logger.info(f"Total Items Collected: {total_items}")
        logger.info(f"YouTube: {pipeline_results['scraping']['youtube_videos']} videos")
        logger.info(f"TikTok: {pipeline_results['scraping']['tiktok_videos']} videos")
        logger.info(f"Instagram: {pipeline_results['scraping']['instagram_posts']} posts")
        logger.info("=" * 80)

        # Create Prefect Artifacts for UI display
        try:
            # 1. Summary Statistics (Markdown)
            summary_md = f"""# 📊 Social Media Collection Summary

## Collection Results
- **Total Items Collected**: {total_items:,}
- **Duration**: {duration:.1f}s
- **Status**: ✅ Success

## Platform Breakdown
| Platform | Items Collected | DB Records |
|----------|----------------|------------|
| 📺 YouTube | {pipeline_results['scraping']['youtube_videos']} videos | {db_stats.get('youtube', {}).get('saved', 0)} |
| 🎵 TikTok | {pipeline_results['scraping']['tiktok_videos']} videos | {db_stats.get('tiktok', {}).get('saved', 0)} |
| 📸 Instagram | {pipeline_results['scraping']['instagram_posts']} posts | {db_stats.get('instagram', {}).get('saved', 0)} |

## Keywords & Hashtags
- **Brand Keywords**: {', '.join(brand_keywords)}
- **Hashtags**: {', '.join(hashtags)}

---
*Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
"""
            await create_markdown_artifact(
                key="social-media-summary",
                markdown=summary_md,
                description="Social media collection summary"
            )

            # 2. Sample Data Tables (Top 5 from each platform)
            # YouTube samples
            if social_data.get('youtube'):
                youtube_samples = []
                for video in social_data['youtube'][:5]:
                    youtube_samples.append({
                        'Video ID': video.get('video_id', '')[:15],
                        'Channel': video.get('channel_title', '')[:30],
                        'Title': video.get('title', '')[:50],
                        'Views': f"{video.get('view_count', 0):,}",
                        'URL': f"[Link]({video.get('video_url', '')})"
                    })

                if youtube_samples:
                    await create_table_artifact(
                        key="youtube-top-videos",
                        table=youtube_samples,
                        description="Top 5 YouTube videos collected"
                    )

            # TikTok samples
            if social_data.get('tiktok'):
                tiktok_samples = []
                for video in social_data['tiktok'][:5]:
                    tiktok_samples.append({
                        'Author': f"@{video.get('author_username', '')}",
                        'Description': video.get('description', '')[:50],
                        'Views': f"{video.get('view_count', 0):,}",
                        'Likes': f"{video.get('like_count', 0):,}",
                        'URL': f"[Link]({video.get('video_url', '')})"
                    })

                if tiktok_samples:
                    await create_table_artifact(
                        key="tiktok-top-videos",
                        table=tiktok_samples,
                        description="Top 5 TikTok videos collected"
                    )

            # Instagram samples
            if social_data.get('instagram'):
                instagram_samples = []
                for post in social_data['instagram'][:5]:
                    instagram_samples.append({
                        'Owner': f"@{post.get('owner_username', '')}",
                        'Caption': post.get('caption', '')[:50],
                        'Likes': f"{post.get('like_count', 0):,}",
                        'Comments': f"{post.get('comment_count', 0):,}",
                        'URL': f"[Link]({post.get('post_url', '')})"
                    })

                if instagram_samples:
                    await create_table_artifact(
                        key="instagram-top-posts",
                        table=instagram_samples,
                        description="Top 5 Instagram posts collected"
                    )

            # 3. Create AI Training Dataset CSV
            logger.info("Creating AI training dataset CSV...")

            # Prepare data for ML
            ml_dataset = []

            # YouTube data
            for video in social_data.get('youtube', []):
                ml_dataset.append({
                    'platform': 'youtube',
                    'content_id': video.get('video_id', ''),
                    'author': video.get('channel_title', ''),
                    'text': video.get('title', '') + ' ' + video.get('description', ''),
                    'title': video.get('title', ''),
                    'description': video.get('description', ''),
                    'hashtags': '',  # YouTube doesn't provide hashtags in this API
                    'view_count': video.get('view_count', 0),
                    'like_count': video.get('like_count', 0),
                    'comment_count': video.get('comment_count', 0),
                    'engagement_score': (
                        video.get('like_count', 0) +
                        video.get('comment_count', 0) * 2
                    ),
                    'posted_at': video.get('published_at', ''),
                    'url': video.get('video_url', ''),
                    'duration_seconds': video.get('duration_seconds', 0),
                })

            # TikTok data
            for video in social_data.get('tiktok', []):
                ml_dataset.append({
                    'platform': 'tiktok',
                    'content_id': video.get('video_id', ''),
                    'author': video.get('author_username', ''),
                    'text': video.get('description', ''),
                    'title': '',
                    'description': video.get('description', ''),
                    'hashtags': video.get('hashtags', ''),
                    'view_count': video.get('view_count', 0),
                    'like_count': video.get('like_count', 0),
                    'comment_count': video.get('comment_count', 0),
                    'engagement_score': (
                        video.get('like_count', 0) +
                        video.get('comment_count', 0) * 2 +
                        video.get('share_count', 0) * 3
                    ),
                    'posted_at': video.get('posted_at', ''),
                    'url': video.get('video_url', ''),
                    'duration_seconds': video.get('duration_seconds', 0),
                })

            # Instagram data
            for post in social_data.get('instagram', []):
                ml_dataset.append({
                    'platform': 'instagram',
                    'content_id': post.get('shortcode', ''),
                    'author': post.get('owner_username', ''),
                    'text': post.get('caption', ''),
                    'title': '',
                    'description': post.get('caption', ''),
                    'hashtags': post.get('hashtags', ''),
                    'view_count': post.get('video_view_count', 0) or 0,
                    'like_count': post.get('like_count', 0),
                    'comment_count': post.get('comment_count', 0),
                    'engagement_score': (
                        post.get('like_count', 0) +
                        post.get('comment_count', 0) * 2
                    ),
                    'posted_at': post.get('posted_at', ''),
                    'url': post.get('post_url', ''),
                    'duration_seconds': 0,
                })

            if ml_dataset:
                # Save to CSV
                df = pd.DataFrame(ml_dataset)

                # Create datasets directory
                dataset_dir = Path("data/datasets")
                dataset_dir.mkdir(parents=True, exist_ok=True)

                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                csv_filename = f"social_media_ml_dataset_{timestamp}.csv"
                csv_path = dataset_dir / csv_filename

                # Save CSV
                df.to_csv(csv_path, index=False, encoding='utf-8')
                logger.info(f"✅ ML Dataset CSV saved: {csv_path}")

                # Create download link artifact
                await create_link_artifact(
                    key="ml-dataset-download",
                    link=str(csv_path),
                    description=f"🤖 AI Training Dataset CSV ({len(ml_dataset)} rows, {len(df.columns)} columns)"
                )

                # Also create summary of dataset
                dataset_summary_md = f"""# 🤖 AI Training Dataset

## Dataset Information
- **Total Records**: {len(ml_dataset):,}
- **Columns**: {len(df.columns)}
- **File**: `{csv_filename}`
- **File Size**: {csv_path.stat().st_size / 1024:.1f} KB

## Platform Distribution
- **YouTube**: {len([r for r in ml_dataset if r['platform'] == 'youtube'])} records
- **TikTok**: {len([r for r in ml_dataset if r['platform'] == 'tiktok'])} records
- **Instagram**: {len([r for r in ml_dataset if r['platform'] == 'instagram'])} records

## Columns
- `platform`: Source platform (youtube/tiktok/instagram)
- `content_id`: Unique content identifier
- `author`: Content creator username/channel
- `text`: Full text content (title + description for analysis)
- `title`: Video/post title
- `description`: Detailed description/caption
- `hashtags`: Comma-separated hashtags
- `view_count`: Number of views
- `like_count`: Number of likes
- `comment_count`: Number of comments
- `engagement_score`: Calculated engagement metric
- `posted_at`: Publication timestamp
- `url`: Content URL
- `duration_seconds`: Video duration (0 for images)

## Top Engaged Content (by engagement_score)
{df.nlargest(5, 'engagement_score')[['platform', 'author', 'engagement_score', 'like_count']].to_markdown(index=False)}

---
**File Path**: `{csv_path}`

**Usage Example**:
```python
import pandas as pd
df = pd.read_csv('{csv_path}')
print(df.head())
```
"""
                await create_markdown_artifact(
                    key="ml-dataset-info",
                    markdown=dataset_summary_md,
                    description="AI Training Dataset Information"
                )

                logger.info(f"✅ ML Dataset artifacts created: {len(ml_dataset)} records")

            logger.info("✅ Prefect artifacts created successfully")

        except Exception as artifact_error:
            logger.warning(f"Failed to create Prefect artifacts: {artifact_error}")
            # Don't fail the flow if artifact creation fails

        return pipeline_results

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        pipeline_results['status'] = 'failed'
        pipeline_results['error'] = str(e)
        pipeline_results['completed_at'] = datetime.now()
        raise


@flow(
    name="social-test-pipeline",
    description="Test social media scraping with limited items",
    log_prints=True
)
async def social_test_pipeline() -> Dict[str, Any]:
    """
    Test flow for social media scraping (limited items)

    This is a lightweight version for testing that collects only 10 items per platform.

    Returns:
        Dictionary with pipeline execution results
    """
    logger.info("Starting Social Media TEST Pipeline (10 items per platform)")

    return await social_pipeline(
        brand_keywords=['laneige'],
        hashtags=['laneige'],
        max_items_per_platform=10
    )


# Individual platform flows for targeted collection

@flow(
    name="youtube-scraping-flow",
    description="YouTube-only scraping flow with comments and captions",
    log_prints=True
)
def youtube_flow(
    query: str = 'laneige',
    max_results: int = 50,
    collect_comments: bool = True,
    collect_captions: bool = True,
    max_comments_per_video: int = 50
) -> Dict[str, Any]:
    """
    YouTube-only scraping flow with comments and captions

    Args:
        query: Search query
        max_results: Max videos to collect
        collect_comments: Whether to collect comments
        collect_captions: Whether to collect captions
        max_comments_per_video: Max comments per video

    Returns:
        Flow execution results
    """
    from src.tasks.social_tasks import (
        scrape_youtube_videos_task,
        scrape_youtube_comments_task,
        scrape_youtube_captions_task
    )
    from src.tasks.processing_tasks import (
        save_youtube_videos_to_db_task,
        save_youtube_comments_to_db_task,
        save_youtube_captions_to_db_task
    )

    logger.info(f"Starting YouTube Flow - query: {query}, max: {max_results}")
    logger.info(f"Collect comments: {collect_comments}, Collect captions: {collect_captions}")

    try:
        # Step 1: Scrape YouTube videos
        videos = scrape_youtube_videos_task(query=query, max_results=max_results)

        # Save videos to DB
        db_stats = save_youtube_videos_to_db_task(videos=videos)

        # Extract video IDs
        video_ids = [video['video_id'] for video in videos]

        # Step 2: Scrape comments (optional)
        comments_stats = {}
        if collect_comments and video_ids:
            comments = scrape_youtube_comments_task(
                video_ids=video_ids,
                max_comments_per_video=max_comments_per_video
            )
            comments_stats = save_youtube_comments_to_db_task(comments)

        # Step 3: Scrape captions (optional)
        captions_stats = {}
        if collect_captions and video_ids:
            captions = scrape_youtube_captions_task(
                video_ids=video_ids,
                languages=['en', 'ko']
            )
            captions_stats = save_youtube_captions_to_db_task(captions)

        logger.info(f"YouTube Flow Complete: {len(videos)} videos")
        logger.info(f"  Videos: {db_stats}")
        logger.info(f"  Comments: {comments_stats}")
        logger.info(f"  Captions: {captions_stats}")

        return {
            'status': 'success',
            'videos_collected': len(videos),
            'database_stats': {
                'videos': db_stats,
                'comments': comments_stats,
                'captions': captions_stats
            }
        }

    except Exception as e:
        logger.error(f"YouTube Flow failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@flow(
    name="tiktok-scraping-flow",
    description="TikTok-only scraping flow",
    log_prints=True
)
async def tiktok_flow(hashtag: str = 'laneige', max_videos: int = 30) -> Dict[str, Any]:
    """
    TikTok-only scraping flow

    Args:
        hashtag: Hashtag to search
        max_videos: Max videos to collect

    Returns:
        Flow execution results
    """
    from src.tasks.social_tasks import scrape_tiktok_hashtag_task
    from src.tasks.processing_tasks import save_tiktok_videos_to_db_task

    logger.info(f"Starting TikTok Flow - hashtag: #{hashtag}, max: {max_videos}")

    try:
        # Scrape TikTok
        videos = await scrape_tiktok_hashtag_task(hashtag=hashtag, max_videos=max_videos)

        # Save to DB
        db_stats = save_tiktok_videos_to_db_task(videos=videos)

        logger.info(f"TikTok Flow Complete: {len(videos)} videos, {db_stats}")

        return {
            'status': 'success',
            'videos_collected': len(videos),
            'database_stats': db_stats
        }

    except Exception as e:
        logger.error(f"TikTok Flow failed: {e}")
        return {'status': 'failed', 'error': str(e)}


@flow(
    name="instagram-scraping-flow",
    description="Instagram-only scraping flow",
    log_prints=True
)
def instagram_flow(hashtag: str = 'laneige', max_posts: int = 50) -> Dict[str, Any]:
    """
    Instagram-only scraping flow

    Args:
        hashtag: Hashtag to search
        max_posts: Max posts to collect

    Returns:
        Flow execution results
    """
    from src.tasks.social_tasks import scrape_instagram_hashtag_task
    from src.tasks.processing_tasks import save_instagram_posts_to_db_task

    logger.info(f"Starting Instagram Flow - hashtag: #{hashtag}, max: {max_posts}")

    try:
        # Scrape Instagram
        posts = scrape_instagram_hashtag_task(hashtag=hashtag, max_posts=max_posts)

        # Save to DB
        db_stats = save_instagram_posts_to_db_task(posts=posts)

        logger.info(f"Instagram Flow Complete: {len(posts)} posts, {db_stats}")

        return {
            'status': 'success',
            'posts_collected': len(posts),
            'database_stats': db_stats
        }

    except Exception as e:
        logger.error(f"Instagram Flow failed: {e}")
        return {'status': 'failed', 'error': str(e)}
