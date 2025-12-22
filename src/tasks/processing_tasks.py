"""
Prefect Tasks for data processing and storage
"""

import json
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

from prefect import task
from loguru import logger
from sqlalchemy import select

from src.core.database import get_db_context
from src.models.amazon import AmazonProduct, AmazonRanking, AmazonCategory
from src.models.brands import Brand
from src.models.social_media import (
    YouTubeVideo, YouTubeMetric, YouTubeComment, YouTubeCaption,
    TikTokPost, TikTokMetric,
    InstagramPost, InstagramMetric
)
from config.settings import settings


@task(
    name="save-products-to-db",
    description="Save scraped products to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_products_to_db_task(
    category_products: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, int]:
    """
    Save scraped products and rankings to database

    Args:
        category_products: Dictionary mapping category names to product lists

    Returns:
        Dictionary with statistics (products_created, rankings_created)
    """
    logger.info("Task: Saving products to database")

    stats = {
        'products_created': 0,
        'products_updated': 0,
        'rankings_created': 0,
        'categories_processed': 0
    }

    try:
        with get_db_context() as db:
            # Get all brands for matching
            brands = db.execute(select(Brand)).scalars().all()
            brand_map = {b.name.lower(): b for b in brands}

            # Get all categories
            categories = db.execute(select(AmazonCategory)).scalars().all()
            category_map = {c.category_name: c for c in categories}

            for category_name, products in category_products.items():
                if category_name not in category_map:
                    logger.warning(f"Category not found in DB: {category_name}")
                    continue

                category = category_map[category_name]
                stats['categories_processed'] += 1

                for product_data in products:
                    # Get or create product
                    product = db.execute(
                        select(AmazonProduct).where(
                            AmazonProduct.asin == product_data['asin']
                        )
                    ).scalar_one_or_none()

                    if not product:
                        # Match brand
                        brand_id = None
                        product_name_lower = product_data['product_name'].lower()
                        for brand_name, brand in brand_map.items():
                            if brand_name in product_name_lower:
                                brand_id = brand.id
                                break

                        # Create new product
                        product = AmazonProduct(
                            asin=product_data['asin'],
                            product_name=product_data['product_name'],
                            brand_id=brand_id,
                            product_url=product_data['product_url'],
                            first_seen_at=datetime.now(),
                            last_seen_at=datetime.now(),
                            is_active=True
                        )
                        db.add(product)
                        db.flush()
                        stats['products_created'] += 1
                    else:
                        # Update existing product
                        now = datetime.now()
                        product.last_seen_at = now
                        product.updated_at = now
                        product.is_active = True
                        stats['products_updated'] += 1

                    # Create ranking record
                    ranking = AmazonRanking(
                        product_id=product.id,
                        category_id=category.id,
                        rank=product_data['rank'],
                        price=product_data.get('price'),
                        rating=product_data.get('rating'),
                        review_count=product_data.get('review_count'),
                        is_prime=product_data.get('is_prime', False),
                        stock_status=product_data.get('stock_status', 'unknown'),
                        collected_at=product_data.get('collected_at', datetime.now())
                    )
                    db.add(ranking)
                    stats['rankings_created'] += 1

                logger.info(f"Processed category: {category_name} - {len(products)} products")

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving to database: {e}")
        raise


@task(
    name="backup-to-json",
    description="Backup scraped data to JSON file",
    log_prints=True
)
def backup_to_json_task(
    category_products: Dict[str, List[Dict[str, Any]]],
    backup_dir: Path = None
) -> str:
    """
    Backup scraped data to JSON file

    Args:
        category_products: Dictionary mapping category names to product lists
        backup_dir: Directory to save backups (default: data/backups)

    Returns:
        Path to backup file
    """
    logger.info("Task: Backing up data to JSON")

    try:
        if backup_dir is None:
            backup_dir = settings.BACKUPS_DIR

        backup_dir.mkdir(parents=True, exist_ok=True)

        # Create filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"amazon_backup_{timestamp}.json"
        filepath = backup_dir / filename

        # Convert datetime objects to strings
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'categories': {}
        }

        for category_name, products in category_products.items():
            # Convert products to serializable format
            serializable_products = []
            for product in products:
                p = product.copy()
                if 'collected_at' in p and isinstance(p['collected_at'], datetime):
                    p['collected_at'] = p['collected_at'].isoformat()
                serializable_products.append(p)

            backup_data['categories'][category_name] = serializable_products

        # Write to file
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, ensure_ascii=False)

        total_products = sum(len(products) for products in category_products.values())
        logger.info(f"Task complete: Backed up {total_products} products to {filepath}")

        return str(filepath)

    except Exception as e:
        logger.error(f"Task failed: Error backing up data: {e}")
        raise


@task(
    name="validate-data",
    description="Validate scraped data quality",
    log_prints=True
)
def validate_data_task(
    category_products: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, Any]:
    """
    Validate scraped data quality

    Args:
        category_products: Dictionary mapping category names to product lists

    Returns:
        Validation report
    """
    logger.info("Task: Validating scraped data")

    report = {
        'total_categories': len(category_products),
        'total_products': 0,
        'valid_products': 0,
        'missing_asin': 0,
        'missing_price': 0,
        'missing_rating': 0,
        'warnings': []
    }

    for category_name, products in category_products.items():
        report['total_products'] += len(products)

        if len(products) == 0:
            report['warnings'].append(f"No products scraped for category: {category_name}")

        for product in products:
            # Check required fields
            if not product.get('asin'):
                report['missing_asin'] += 1
                continue

            if not product.get('price'):
                report['missing_price'] += 1

            if not product.get('rating'):
                report['missing_rating'] += 1

            # Count as valid if has ASIN and product name
            if product.get('asin') and product.get('product_name'):
                report['valid_products'] += 1

    # Calculate percentages
    if report['total_products'] > 0:
        report['valid_percentage'] = (report['valid_products'] / report['total_products']) * 100
    else:
        report['valid_percentage'] = 0

    logger.info(f"Task complete: Validation report: {report['valid_products']}/{report['total_products']} valid products ({report['valid_percentage']:.1f}%)")

    return report


# ===========================
# Social Media Processing Tasks
# ===========================

@task(
    name="save-youtube-videos-to-db",
    description="Save YouTube videos and metrics to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_youtube_videos_to_db_task(
    videos: List[Dict[str, Any]],
    brand_name: str = "Laneige"
) -> Dict[str, int]:
    """
    Save YouTube videos and metrics to database

    Args:
        videos: List of video data dictionaries
        brand_name: Brand name to associate videos with

    Returns:
        Dictionary with statistics
    """
    logger.info(f"Task: Saving {len(videos)} YouTube videos to database")

    stats = {
        'videos_created': 0,
        'videos_updated': 0,
        'metrics_created': 0
    }

    try:
        with get_db_context() as db:
            # Get brand
            brand = db.execute(
                select(Brand).where(Brand.name == brand_name)
            ).scalar_one_or_none()

            if not brand:
                logger.warning(f"Brand not found: {brand_name}")
                brand_id = None
            else:
                brand_id = brand.id

            for video_data in videos:
                # Get or create video
                video = db.execute(
                    select(YouTubeVideo).where(
                        YouTubeVideo.video_id == video_data['video_id']
                    )
                ).scalar_one_or_none()

                if not video:
                    # Create new video
                    video = YouTubeVideo(
                        video_id=video_data['video_id'],
                        brand_id=brand_id,
                        channel_id=video_data.get('channel_id'),
                        channel_title=video_data.get('channel_title'),
                        title=video_data['title'],
                        description=video_data.get('description'),
                        tags=video_data.get('tags'),
                        video_url=video_data.get('video_url'),
                        thumbnail_url=video_data.get('thumbnail_url'),
                        duration_seconds=video_data.get('duration_seconds'),
                        published_at=video_data.get('published_at'),
                        first_seen_at=datetime.now(),
                        last_collected_at=datetime.now(),
                        is_active=True
                    )
                    db.add(video)
                    db.flush()
                    stats['videos_created'] += 1
                else:
                    # Update existing video
                    video.last_collected_at = datetime.now()
                    video.is_active = True
                    stats['videos_updated'] += 1

                # Create metrics record
                metric = YouTubeMetric(
                    video_id=video.id,
                    view_count=video_data.get('view_count', 0),
                    like_count=video_data.get('like_count', 0),
                    comment_count=video_data.get('comment_count', 0),
                    favorite_count=video_data.get('favorite_count', 0),
                    collected_at=datetime.now()
                )
                db.add(metric)
                stats['metrics_created'] += 1

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving YouTube data: {e}")
        raise


@task(
    name="save-tiktok-videos-to-db",
    description="Save TikTok videos and metrics to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_tiktok_videos_to_db_task(
    videos: List[Dict[str, Any]],
    brand_name: str = "Laneige"
) -> Dict[str, int]:
    """
    Save TikTok videos and metrics to database

    Args:
        videos: List of video data dictionaries
        brand_name: Brand name to associate videos with

    Returns:
        Dictionary with statistics
    """
    logger.info(f"Task: Saving {len(videos)} TikTok videos to database")

    stats = {
        'videos_created': 0,
        'videos_updated': 0,
        'metrics_created': 0
    }

    try:
        with get_db_context() as db:
            # Get brand
            brand = db.execute(
                select(Brand).where(Brand.name == brand_name)
            ).scalar_one_or_none()

            if not brand:
                logger.warning(f"Brand not found: {brand_name}")
                brand_id = None
            else:
                brand_id = brand.id

            for video_data in videos:
                # Get or create post
                post = db.execute(
                    select(TikTokPost).where(
                        TikTokPost.video_id == video_data['video_id']
                    )
                ).scalar_one_or_none()

                if not post:
                    # Create new post
                    post = TikTokPost(
                        video_id=video_data['video_id'],
                        brand_id=brand_id,
                        author_username=video_data.get('author_username'),
                        description=video_data.get('description'),
                        hashtags=video_data.get('hashtags'),
                        video_url=video_data.get('video_url'),
                        thumbnail_url=video_data.get('thumbnail_url'),
                        duration_seconds=video_data.get('duration_seconds'),
                        posted_at=video_data.get('posted_at'),
                        first_seen_at=datetime.now(),
                        last_collected_at=datetime.now(),
                        is_active=True
                    )
                    db.add(post)
                    db.flush()
                    stats['videos_created'] += 1
                else:
                    # Update existing post
                    post.last_collected_at = datetime.now()
                    post.is_active = True
                    stats['videos_updated'] += 1

                # Create metrics record
                metric = TikTokMetric(
                    post_id=post.id,
                    view_count=video_data.get('view_count', 0),
                    like_count=video_data.get('like_count', 0),
                    comment_count=video_data.get('comment_count', 0),
                    share_count=video_data.get('share_count', 0),
                    play_count=video_data.get('play_count', 0),
                    collected_at=datetime.now()
                )
                db.add(metric)
                stats['metrics_created'] += 1

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving TikTok data: {e}")
        raise


@task(
    name="save-instagram-posts-to-db",
    description="Save Instagram posts and metrics to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_instagram_posts_to_db_task(
    posts: List[Dict[str, Any]],
    brand_name: str = "Laneige"
) -> Dict[str, int]:
    """
    Save Instagram posts and metrics to database

    Args:
        posts: List of post data dictionaries
        brand_name: Brand name to associate posts with

    Returns:
        Dictionary with statistics
    """
    logger.info(f"Task: Saving {len(posts)} Instagram posts to database")

    stats = {
        'posts_created': 0,
        'posts_updated': 0,
        'metrics_created': 0
    }

    try:
        with get_db_context() as db:
            # Get brand
            brand = db.execute(
                select(Brand).where(Brand.name == brand_name)
            ).scalar_one_or_none()

            if not brand:
                logger.warning(f"Brand not found: {brand_name}")
                brand_id = None
            else:
                brand_id = brand.id

            for post_data in posts:
                # Get or create post
                post = db.execute(
                    select(InstagramPost).where(
                        InstagramPost.shortcode == post_data['shortcode']
                    )
                ).scalar_one_or_none()

                if not post:
                    # Create new post
                    post = InstagramPost(
                        shortcode=post_data['shortcode'],
                        brand_id=brand_id,
                        owner_username=post_data.get('owner_username'),
                        owner_id=post_data.get('owner_id'),
                        caption=post_data.get('caption'),
                        hashtags=post_data.get('hashtags'),
                        post_url=post_data.get('post_url'),
                        media_type=post_data.get('media_type'),
                        media_url=post_data.get('media_url'),
                        posted_at=post_data.get('posted_at'),
                        first_seen_at=datetime.now(),
                        last_collected_at=datetime.now(),
                        is_active=True
                    )
                    db.add(post)
                    db.flush()
                    stats['posts_created'] += 1
                else:
                    # Update existing post
                    post.last_collected_at = datetime.now()
                    post.is_active = True
                    stats['posts_updated'] += 1

                # Create metrics record
                metric = InstagramMetric(
                    post_id=post.id,
                    like_count=post_data.get('like_count', 0),
                    comment_count=post_data.get('comment_count', 0),
                    video_view_count=post_data.get('video_view_count'),
                    collected_at=datetime.now()
                )
                db.add(metric)
                stats['metrics_created'] += 1

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving Instagram data: {e}")
        raise


@task(
    name="save-all-social-media-to-db",
    description="Save all social media data to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_all_social_media_to_db_task(
    social_data: Dict[str, List[Dict[str, Any]]],
    brand_name: str = "Laneige"
) -> Dict[str, Dict[str, int]]:
    """
    Save all social media platform data to database

    Args:
        social_data: Dictionary with platform data {'youtube': [...], 'tiktok': [...], 'instagram': [...]}
        brand_name: Brand name

    Returns:
        Dictionary with statistics per platform
    """
    logger.info("Task: Saving all social media data to database")

    all_stats = {}

    # Save YouTube
    if 'youtube' in social_data and social_data['youtube']:
        youtube_stats = save_youtube_videos_to_db_task(social_data['youtube'], brand_name)
        all_stats['youtube'] = youtube_stats

    # Save TikTok
    if 'tiktok' in social_data and social_data['tiktok']:
        tiktok_stats = save_tiktok_videos_to_db_task(social_data['tiktok'], brand_name)
        all_stats['tiktok'] = tiktok_stats

    # Save Instagram
    if 'instagram' in social_data and social_data['instagram']:
        instagram_stats = save_instagram_posts_to_db_task(social_data['instagram'], brand_name)
        all_stats['instagram'] = instagram_stats

    logger.info(f"Task complete: Saved all social media data: {all_stats}")
    return all_stats


@task(
    name="save-youtube-comments-to-db",
    description="Save YouTube comments to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_youtube_comments_to_db_task(
    comments_by_video: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, int]:
    """
    Save YouTube comments to database

    Args:
        comments_by_video: Dictionary mapping video_id to list of comments

    Returns:
        Statistics dictionary
    """
    logger.info(f"Task: Saving YouTube comments for {len(comments_by_video)} videos")

    stats = {
        'comments_created': 0,
        'comments_updated': 0,
        'videos_processed': 0
    }

    try:
        with get_db_context() as db:
            for video_id, comments in comments_by_video.items():
                # Get video from DB
                video = db.execute(
                    select(YouTubeVideo).where(YouTubeVideo.video_id == video_id)
                ).scalar_one_or_none()

                if not video:
                    logger.warning(f"Video not found in DB: {video_id}")
                    continue

                stats['videos_processed'] += 1

                for comment_data in comments:
                    # Get or create comment
                    comment = db.execute(
                        select(YouTubeComment).where(
                            YouTubeComment.comment_id == comment_data['comment_id']
                        )
                    ).scalar_one_or_none()

                    if not comment:
                        # Create new comment
                        comment = YouTubeComment(
                            video_id=video.id,
                            comment_id=comment_data['comment_id'],
                            author_name=comment_data.get('author_name'),
                            author_channel_id=comment_data.get('author_channel_id'),
                            text=comment_data.get('text', ''),
                            like_count=comment_data.get('like_count', 0),
                            reply_count=comment_data.get('reply_count', 0),
                            published_at=comment_data.get('published_at'),
                            updated_at=comment_data.get('updated_at'),
                            is_top_level=comment_data.get('is_top_level', True),
                            parent_comment_id=comment_data.get('parent_comment_id'),
                            collected_at=datetime.now()
                        )
                        db.add(comment)
                        stats['comments_created'] += 1
                    else:
                        # Update existing comment
                        comment.like_count = comment_data.get('like_count', 0)
                        comment.reply_count = comment_data.get('reply_count', 0)
                        comment.updated_at = comment_data.get('updated_at')
                        comment.collected_at = datetime.now()
                        stats['comments_updated'] += 1

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving YouTube comments: {e}")
        raise


@task(
    name="save-youtube-captions-to-db",
    description="Save YouTube captions to database",
    retries=2,
    retry_delay_seconds=30,
    log_prints=True
)
def save_youtube_captions_to_db_task(
    captions_by_video: Dict[str, List[Dict[str, Any]]]
) -> Dict[str, int]:
    """
    Save YouTube captions to database

    Args:
        captions_by_video: Dictionary mapping video_id to list of captions

    Returns:
        Statistics dictionary
    """
    logger.info(f"Task: Saving YouTube captions for {len(captions_by_video)} videos")

    stats = {
        'captions_created': 0,
        'captions_updated': 0,
        'videos_processed': 0
    }

    try:
        with get_db_context() as db:
            for video_id, captions in captions_by_video.items():
                # Get video from DB
                video = db.execute(
                    select(YouTubeVideo).where(YouTubeVideo.video_id == video_id)
                ).scalar_one_or_none()

                if not video:
                    logger.warning(f"Video not found in DB: {video_id}")
                    continue

                stats['videos_processed'] += 1

                for caption_data in captions:
                    # Check if caption already exists
                    existing = db.execute(
                        select(YouTubeCaption).where(
                            YouTubeCaption.video_id == video.id,
                            YouTubeCaption.language == caption_data['language']
                        )
                    ).scalar_one_or_none()

                    if not existing:
                        # Create new caption
                        caption = YouTubeCaption(
                            video_id=video.id,
                            language=caption_data['language'],
                            caption_text=caption_data['caption_text'],
                            is_auto_generated=caption_data.get('is_auto_generated', False),
                            collected_at=datetime.now()
                        )
                        db.add(caption)
                        stats['captions_created'] += 1
                    else:
                        # Update existing caption
                        existing.caption_text = caption_data['caption_text']
                        existing.is_auto_generated = caption_data.get('is_auto_generated', False)
                        existing.collected_at = datetime.now()
                        stats['captions_updated'] += 1

            db.commit()

        logger.info(f"Task complete: {stats}")
        return stats

    except Exception as e:
        logger.error(f"Task failed: Error saving YouTube captions: {e}")
        raise
