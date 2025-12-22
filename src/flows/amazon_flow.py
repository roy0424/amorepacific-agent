"""
Amazon Scraping Flow - Complete pipeline for Amazon data collection
"""

from typing import Dict, List, Any
from datetime import datetime

from prefect import flow
from loguru import logger

from src.tasks.scraping_tasks import scrape_all_amazon_categories_task
from src.tasks.processing_tasks import (
    save_products_to_db_task,
    backup_to_json_task,
    validate_data_task
)


@flow(
    name="amazon-scraping-pipeline",
    description="Complete Amazon Best Sellers scraping and processing pipeline",
    log_prints=True,
    retries=1,
    retry_delay_seconds=300
)
async def amazon_pipeline() -> Dict[str, Any]:
    """
    Complete Amazon scraping pipeline

    This flow:
    1. Scrapes all configured Amazon Best Sellers categories
    2. Validates the scraped data
    3. Saves products and rankings to database
    4. Creates JSON backup

    Returns:
        Dictionary with pipeline execution results
    """
    logger.info("=" * 80)
    logger.info("Starting Amazon Scraping Pipeline")
    logger.info(f"Timestamp: {datetime.now()}")
    logger.info("=" * 80)

    pipeline_results = {
        'started_at': datetime.now(),
        'status': 'running',
        'scraping': {},
        'validation': {},
        'database': {},
        'backup': {}
    }

    try:
        # Step 1: Scrape all Amazon categories
        logger.info("Step 1/4: Scraping Amazon categories...")
        category_products = await scrape_all_amazon_categories_task()

        total_products = sum(len(products) for products in category_products.values())
        pipeline_results['scraping'] = {
            'categories_scraped': len(category_products),
            'total_products': total_products,
            'status': 'success'
        }
        logger.info(f"Scraping complete: {total_products} products from {len(category_products)} categories")

        # Step 2: Validate data quality
        logger.info("Step 2/4: Validating data quality...")
        validation_report = validate_data_task(category_products)
        pipeline_results['validation'] = validation_report
        logger.info(f"Validation complete: {validation_report['valid_products']}/{validation_report['total_products']} valid products")

        # Step 3: Save to database
        logger.info("Step 3/4: Saving to database...")
        db_stats = save_products_to_db_task(category_products)
        pipeline_results['database'] = db_stats
        logger.info(f"Database save complete: {db_stats['rankings_created']} rankings created")

        # Step 4: Create JSON backup
        logger.info("Step 4/4: Creating backup...")
        backup_path = backup_to_json_task(category_products)
        pipeline_results['backup'] = {
            'backup_path': backup_path,
            'status': 'success'
        }
        logger.info(f"Backup complete: {backup_path}")

        # Mark pipeline as successful
        pipeline_results['status'] = 'success'
        pipeline_results['completed_at'] = datetime.now()

        # Calculate duration
        duration = (pipeline_results['completed_at'] - pipeline_results['started_at']).total_seconds()
        pipeline_results['duration_seconds'] = duration

        logger.info("=" * 80)
        logger.info(f"Amazon Pipeline Complete - Duration: {duration:.1f}s")
        logger.info(f"Total Products: {total_products}")
        logger.info(f"Valid Products: {validation_report['valid_products']}")
        logger.info(f"Rankings Created: {db_stats['rankings_created']}")
        logger.info("=" * 80)

        return pipeline_results

    except Exception as e:
        logger.error(f"Pipeline failed: {e}")
        pipeline_results['status'] = 'failed'
        pipeline_results['error'] = str(e)
        pipeline_results['completed_at'] = datetime.now()
        raise


@flow(
    name="amazon-scraping-quick-test",
    description="Quick test of Amazon scraping (single category, 10 products)",
    log_prints=True
)
async def amazon_quick_test() -> Dict[str, Any]:
    """
    Quick test flow for development

    Scrapes only the first category with limited products
    """
    from config.settings import settings
    from src.tasks.scraping_tasks import scrape_amazon_category_task

    logger.info("Running quick test of Amazon scraper...")

    # Get first category
    first_category = list(settings.AMAZON_CATEGORIES.values())[0]

    # Scrape with limited products
    products = await scrape_amazon_category_task(
        category_name=first_category['name'],
        category_url=first_category['url'],
        max_products=100  # Test full pagination (2 pages)
    )

    logger.info(f"Test complete: Scraped {len(products)} products")

    # Print sample products
    for i, product in enumerate(products[:3], 1):
        logger.info(f"  {i}. [{product['rank']}] {product['product_name'][:50]}...")
        logger.info(f"     ASIN: {product['asin']}, Price: ${product.get('price', 'N/A')}")

    return {
        'products_scraped': len(products),
        'sample_products': products[:3]
    }


if __name__ == "__main__":
    import asyncio

    # Run quick test
    asyncio.run(amazon_quick_test())
