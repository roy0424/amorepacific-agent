#!/usr/bin/env python3
"""
Check data quality - verify all columns are properly populated
"""

import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker
from loguru import logger

from config.settings import settings
from src.models.social_media import (
    YouTubeVideo,
    YouTubeMetric,
    TikTokPost,
    TikTokMetric,
    InstagramPost,
    InstagramMetric
)


def check_column_completeness(session, model, metric_model=None, name=""):
    """Check if columns are properly populated"""

    logger.info(f"\n{'='*80}")
    logger.info(f"📊 {name} Data Quality Check")
    logger.info(f"{'='*80}")

    # Get total count
    total = session.query(model).count()
    logger.info(f"\nTotal records: {total}")

    if total == 0:
        logger.warning("No data to check!")
        return

    # Get a sample record
    sample = session.query(model).first()

    logger.info(f"\n🔍 Sample Record Inspection:")
    logger.info(f"{'='*80}")

    # Get all columns
    inspector = inspect(model)
    columns = [c.key for c in inspector.columns]

    # Check each column
    null_counts = {}
    for col in columns:
        null_count = session.query(model).filter(
            getattr(model, col) == None
        ).count()
        null_counts[col] = null_count

        sample_value = getattr(sample, col)

        # Format output
        status = "✅" if null_count == 0 else f"⚠️  ({null_count}/{total} null)"

        # Show sample value (truncate if too long)
        if sample_value is not None:
            str_value = str(sample_value)
            if len(str_value) > 60:
                str_value = str_value[:60] + "..."
        else:
            str_value = "NULL"

        logger.info(f"  {col:25s} {status:20s} Sample: {str_value}")

    # Check metrics if provided
    if metric_model:
        logger.info(f"\n📈 Metrics Table Check:")
        logger.info(f"{'='*80}")

        metric_total = session.query(metric_model).count()
        logger.info(f"Total metric records: {metric_total}")

        if metric_total > 0:
            sample_metric = session.query(metric_model).first()

            metric_inspector = inspect(metric_model)
            metric_columns = [c.key for c in metric_inspector.columns]

            for col in metric_columns:
                null_count = session.query(metric_model).filter(
                    getattr(metric_model, col) == None
                ).count()

                sample_value = getattr(sample_metric, col)
                status = "✅" if null_count == 0 else f"⚠️  ({null_count}/{metric_total} null)"

                if sample_value is not None:
                    str_value = str(sample_value)
                    if len(str_value) > 60:
                        str_value = str_value[:60] + "..."
                else:
                    str_value = "NULL"

                logger.info(f"  {col:25s} {status:20s} Sample: {str_value}")

    # Critical fields check
    logger.info(f"\n⚠️  Critical Fields Analysis:")
    logger.info(f"{'='*80}")

    critical_issues = []

    # Check for empty critical fields
    if name == "YouTube":
        if null_counts.get('video_id', 0) > 0:
            critical_issues.append(f"video_id has {null_counts['video_id']} nulls")
        if null_counts.get('title', 0) > 0:
            critical_issues.append(f"title has {null_counts['title']} nulls")

    elif name == "TikTok":
        if null_counts.get('video_id', 0) > 0:
            critical_issues.append(f"video_id has {null_counts['video_id']} nulls")
        if null_counts.get('author_username', 0) > 0:
            critical_issues.append(f"author_username has {null_counts['author_username']} nulls")

    elif name == "Instagram":
        if null_counts.get('shortcode', 0) > 0:
            critical_issues.append(f"shortcode has {null_counts['shortcode']} nulls")
        if null_counts.get('owner_username', 0) > 0:
            critical_issues.append(f"owner_username has {null_counts['owner_username']} nulls")

    if critical_issues:
        logger.error(f"❌ Critical issues found:")
        for issue in critical_issues:
            logger.error(f"   - {issue}")
    else:
        logger.success(f"✅ All critical fields populated!")

    # Show some example records
    logger.info(f"\n📝 Sample Records (first 3):")
    logger.info(f"{'='*80}")

    samples = session.query(model).limit(3).all()
    for i, record in enumerate(samples, 1):
        logger.info(f"\nRecord {i}:")
        record_dict = record.to_dict() if hasattr(record, 'to_dict') else {}
        for key, value in list(record_dict.items())[:8]:  # Show first 8 fields
            if value is not None:
                str_value = str(value)
                if len(str_value) > 50:
                    str_value = str_value[:50] + "..."
            else:
                str_value = "NULL"
            logger.info(f"  {key}: {str_value}")


def main():
    """Main entry point"""

    # Create database connection
    engine = create_engine(settings.DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Check YouTube
        check_column_completeness(
            session,
            YouTubeVideo,
            YouTubeMetric,
            "YouTube"
        )

        # Check TikTok
        check_column_completeness(
            session,
            TikTokPost,
            TikTokMetric,
            "TikTok"
        )

        # Check Instagram
        check_column_completeness(
            session,
            InstagramPost,
            InstagramMetric,
            "Instagram"
        )

        logger.info(f"\n{'='*80}")
        logger.success("✅ Data Quality Check Complete!")
        logger.info(f"{'='*80}")

    except Exception as e:
        logger.error(f"Error checking data quality: {e}")
        import traceback
        traceback.print_exc()

    finally:
        session.close()


if __name__ == "__main__":
    main()
