"""
데이터 추출 스크립트
수집된 데이터를 CSV/Excel로 추출하여 팀원들이 분석할 수 있도록 합니다.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

import argparse
from datetime import datetime, timedelta
from typing import List, Dict, Any
import pandas as pd
from loguru import logger
from sqlalchemy import select

from src.core.database import get_db_context
from src.models.amazon import AmazonProduct, AmazonRanking, AmazonCategory
from src.models.brands import Brand
from src.models.social_media import (
    YouTubeVideo, YouTubeMetric,
    TikTokPost, TikTokMetric,
    InstagramPost, InstagramMetric
)
from config.settings import settings


def export_amazon_data(
    output_dir: Path,
    days: int = 7,
    format: str = "csv"
) -> List[str]:
    """
    Amazon 데이터를 추출합니다.

    Args:
        output_dir: 출력 디렉토리
        days: 최근 N일간 데이터 (기본: 7일)
        format: 파일 형식 ("csv" 또는 "excel")

    Returns:
        생성된 파일 경로 리스트
    """
    logger.info(f"Exporting Amazon data (last {days} days)...")

    files_created = []
    cutoff_date = datetime.now() - timedelta(days=days)

    with get_db_context() as db:
        # 1. 제품 목록 추출
        logger.info("  - Extracting products...")
        products_query = (
            select(AmazonProduct, Brand)
            .outerjoin(Brand, AmazonProduct.brand_id == Brand.id)
        )
        products_result = db.execute(products_query).all()

        products_data = []
        for product, brand in products_result:
            products_data.append({
                'ASIN': product.asin,
                'Product Name': product.product_name,
                'Brand': brand.name if brand else 'Unknown',
                'Product URL': product.product_url,
                'First Seen': product.first_seen_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Last Seen': product.last_seen_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Is Active': product.is_active
            })

        df_products = pd.DataFrame(products_data)

        # 2. 랭킹 데이터 추출 (시계열)
        logger.info("  - Extracting rankings...")
        rankings_query = (
            select(
                AmazonRanking,
                AmazonProduct,
                AmazonCategory,
                Brand
            )
            .join(AmazonProduct, AmazonRanking.product_id == AmazonProduct.id)
            .join(AmazonCategory, AmazonRanking.category_id == AmazonCategory.id)
            .outerjoin(Brand, AmazonProduct.brand_id == Brand.id)
            .where(AmazonRanking.collected_at >= cutoff_date)
            .order_by(AmazonRanking.collected_at.desc())
        )
        rankings_result = db.execute(rankings_query).all()

        rankings_data = []
        for ranking, product, category, brand in rankings_result:
            rankings_data.append({
                'Collected At': ranking.collected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Category': category.category_name,
                'Rank': ranking.rank,
                'ASIN': product.asin,
                'Product Name': product.product_name,
                'Brand': brand.name if brand else 'Unknown',
                'Price': ranking.price,
                'Rating': ranking.rating,
                'Review Count': ranking.review_count,
                'Is Prime': ranking.is_prime,
                'Stock Status': ranking.stock_status
            })

        df_rankings = pd.DataFrame(rankings_data)

        # 3. 브랜드별 랭킹 요약
        logger.info("  - Creating brand summary...")
        if not df_rankings.empty:
            # 최신 데이터만 사용
            latest_date = pd.to_datetime(df_rankings['Collected At']).max()
            df_latest = df_rankings[
                pd.to_datetime(df_rankings['Collected At']) == latest_date
            ]

            brand_summary = df_latest.groupby(['Brand', 'Category']).agg({
                'Rank': 'min',
                'Product Name': 'count'
            }).reset_index()
            brand_summary.columns = ['Brand', 'Category', 'Best Rank', 'Product Count']
            brand_summary = brand_summary.sort_values(['Brand', 'Best Rank'])
        else:
            brand_summary = pd.DataFrame()

    # 파일 저장
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    if format == "excel":
        # Excel 파일 (모든 시트 포함)
        excel_path = output_dir / f"amazon_data_{timestamp}.xlsx"
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            df_products.to_excel(writer, sheet_name='Products', index=False)
            df_rankings.to_excel(writer, sheet_name='Rankings', index=False)
            if not brand_summary.empty:
                brand_summary.to_excel(writer, sheet_name='Brand Summary', index=False)

        files_created.append(str(excel_path))
        logger.info(f"  ✓ Saved: {excel_path}")

    else:  # CSV
        # 여러 CSV 파일
        products_path = output_dir / f"amazon_products_{timestamp}.csv"
        rankings_path = output_dir / f"amazon_rankings_{timestamp}.csv"

        df_products.to_csv(products_path, index=False, encoding='utf-8-sig')
        df_rankings.to_csv(rankings_path, index=False, encoding='utf-8-sig')

        files_created.extend([str(products_path), str(rankings_path)])
        logger.info(f"  ✓ Saved: {products_path}")
        logger.info(f"  ✓ Saved: {rankings_path}")

        if not brand_summary.empty:
            summary_path = output_dir / f"amazon_brand_summary_{timestamp}.csv"
            brand_summary.to_csv(summary_path, index=False, encoding='utf-8-sig')
            files_created.append(str(summary_path))
            logger.info(f"  ✓ Saved: {summary_path}")

    logger.info(f"Amazon export complete: {len(df_products)} products, {len(df_rankings)} rankings")
    return files_created


def export_social_media_data(
    output_dir: Path,
    days: int = 7,
    format: str = "csv"
) -> List[str]:
    """
    소셜미디어 데이터를 추출합니다.

    Args:
        output_dir: 출력 디렉토리
        days: 최근 N일간 데이터
        format: 파일 형식

    Returns:
        생성된 파일 경로 리스트
    """
    logger.info(f"Exporting social media data (last {days} days)...")

    files_created = []
    cutoff_date = datetime.now() - timedelta(days=days)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    with get_db_context() as db:
        # YouTube 데이터
        logger.info("  - Extracting YouTube data...")
        youtube_query = (
            select(YouTubeVideo, YouTubeMetric, Brand)
            .join(YouTubeMetric, YouTubeVideo.id == YouTubeMetric.video_id)
            .outerjoin(Brand, YouTubeVideo.brand_id == Brand.id)
            .where(YouTubeMetric.collected_at >= cutoff_date)
            .order_by(YouTubeMetric.collected_at.desc())
        )
        youtube_result = db.execute(youtube_query).all()

        youtube_data = []
        for video, metric, brand in youtube_result:
            youtube_data.append({
                'Collected At': metric.collected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Video ID': video.video_id,
                'Brand': brand.name if brand else 'Unknown',
                'Channel': video.channel_title,
                'Title': video.title,
                'Published At': video.published_at.strftime('%Y-%m-%d') if video.published_at else '',
                'View Count': metric.view_count,
                'Like Count': metric.like_count,
                'Comment Count': metric.comment_count,
                'Video URL': video.video_url
            })

        df_youtube = pd.DataFrame(youtube_data)

        # TikTok 데이터
        logger.info("  - Extracting TikTok data...")
        tiktok_query = (
            select(TikTokPost, TikTokMetric, Brand)
            .join(TikTokMetric, TikTokPost.id == TikTokMetric.post_id)
            .outerjoin(Brand, TikTokPost.brand_id == Brand.id)
            .where(TikTokMetric.collected_at >= cutoff_date)
            .order_by(TikTokMetric.collected_at.desc())
        )
        tiktok_result = db.execute(tiktok_query).all()

        tiktok_data = []
        for post, metric, brand in tiktok_result:
            tiktok_data.append({
                'Collected At': metric.collected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Video ID': post.video_id,
                'Brand': brand.name if brand else 'Unknown',
                'Author': post.author_username,
                'Description': post.description,
                'Hashtags': post.hashtags,
                'Posted At': post.posted_at.strftime('%Y-%m-%d') if post.posted_at else '',
                'View Count': metric.view_count,
                'Like Count': metric.like_count,
                'Comment Count': metric.comment_count,
                'Share Count': metric.share_count,
                'Video URL': post.video_url
            })

        df_tiktok = pd.DataFrame(tiktok_data)

        # Instagram 데이터
        logger.info("  - Extracting Instagram data...")
        instagram_query = (
            select(InstagramPost, InstagramMetric, Brand)
            .join(InstagramMetric, InstagramPost.id == InstagramMetric.post_id)
            .outerjoin(Brand, InstagramPost.brand_id == Brand.id)
            .where(InstagramMetric.collected_at >= cutoff_date)
            .order_by(InstagramMetric.collected_at.desc())
        )
        instagram_result = db.execute(instagram_query).all()

        instagram_data = []
        for post, metric, brand in instagram_result:
            instagram_data.append({
                'Collected At': metric.collected_at.strftime('%Y-%m-%d %H:%M:%S'),
                'Shortcode': post.shortcode,
                'Brand': brand.name if brand else 'Unknown',
                'Owner': post.owner_username,
                'Caption': post.caption,
                'Hashtags': post.hashtags,
                'Media Type': post.media_type,
                'Posted At': post.posted_at.strftime('%Y-%m-%d') if post.posted_at else '',
                'Like Count': metric.like_count,
                'Comment Count': metric.comment_count,
                'Video View Count': metric.video_view_count,
                'Post URL': post.post_url
            })

        df_instagram = pd.DataFrame(instagram_data)

    # 파일 저장
    if format == "excel":
        excel_path = output_dir / f"social_media_data_{timestamp}.xlsx"
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            if not df_youtube.empty:
                df_youtube.to_excel(writer, sheet_name='YouTube', index=False)
            if not df_tiktok.empty:
                df_tiktok.to_excel(writer, sheet_name='TikTok', index=False)
            if not df_instagram.empty:
                df_instagram.to_excel(writer, sheet_name='Instagram', index=False)

        files_created.append(str(excel_path))
        logger.info(f"  ✓ Saved: {excel_path}")

    else:  # CSV
        if not df_youtube.empty:
            youtube_path = output_dir / f"youtube_data_{timestamp}.csv"
            df_youtube.to_csv(youtube_path, index=False, encoding='utf-8-sig')
            files_created.append(str(youtube_path))
            logger.info(f"  ✓ Saved: {youtube_path}")

        if not df_tiktok.empty:
            tiktok_path = output_dir / f"tiktok_data_{timestamp}.csv"
            df_tiktok.to_csv(tiktok_path, index=False, encoding='utf-8-sig')
            files_created.append(str(tiktok_path))
            logger.info(f"  ✓ Saved: {tiktok_path}")

        if not df_instagram.empty:
            instagram_path = output_dir / f"instagram_data_{timestamp}.csv"
            df_instagram.to_csv(instagram_path, index=False, encoding='utf-8-sig')
            files_created.append(str(instagram_path))
            logger.info(f"  ✓ Saved: {instagram_path}")

    logger.info(f"Social media export complete: YouTube={len(df_youtube)}, TikTok={len(df_tiktok)}, Instagram={len(df_instagram)}")
    return files_created


def main():
    parser = argparse.ArgumentParser(
        description="수집된 데이터를 CSV/Excel로 추출합니다"
    )
    parser.add_argument(
        '--platform',
        choices=['all', 'amazon', 'social'],
        default='all',
        help='추출할 플랫폼 (기본: all)'
    )
    parser.add_argument(
        '--format',
        choices=['csv', 'excel'],
        default='excel',
        help='파일 형식 (기본: excel)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='최근 N일간 데이터 (기본: 7일)'
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='출력 디렉토리 (기본: data/exports)'
    )

    args = parser.parse_args()

    # 출력 디렉토리 설정
    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        output_dir = settings.DATA_DIR / 'exports'

    output_dir.mkdir(parents=True, exist_ok=True)

    logger.info("=" * 80)
    logger.info("Data Export Script")
    logger.info(f"Platform: {args.platform}")
    logger.info(f"Format: {args.format}")
    logger.info(f"Days: {args.days}")
    logger.info(f"Output: {output_dir}")
    logger.info("=" * 80)

    all_files = []

    try:
        # Amazon 데이터 추출
        if args.platform in ['all', 'amazon']:
            amazon_files = export_amazon_data(
                output_dir=output_dir,
                days=args.days,
                format=args.format
            )
            all_files.extend(amazon_files)

        # 소셜미디어 데이터 추출
        if args.platform in ['all', 'social']:
            social_files = export_social_media_data(
                output_dir=output_dir,
                days=args.days,
                format=args.format
            )
            all_files.extend(social_files)

        # 완료 메시지
        logger.info("=" * 80)
        logger.info(f"✅ Export complete! {len(all_files)} files created:")
        for filepath in all_files:
            logger.info(f"   - {filepath}")
        logger.info("=" * 80)

    except Exception as e:
        logger.error(f"❌ Export failed: {e}")
        raise


if __name__ == "__main__":
    main()