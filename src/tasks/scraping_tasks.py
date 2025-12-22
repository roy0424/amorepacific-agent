"""
Prefect Tasks for web scraping
"""

from typing import Dict, List, Any
from datetime import datetime

from prefect import task
from loguru import logger

from src.scrapers.amazon import AmazonScraper


@task(
    name="scrape-amazon-category",
    description="Scrape a single Amazon Best Sellers category",
    retries=3,
    retry_delay_seconds=60,
    timeout_seconds=300,
    log_prints=True
)
async def scrape_amazon_category_task(
    category_name: str,
    category_url: str,
    max_products: int = 100
) -> List[Dict[str, Any]]:
    """
    Scrape a single Amazon category

    Args:
        category_name: Name of the category
        category_url: Best Sellers page URL
        max_products: Maximum number of products to scrape (default: 100)

    Returns:
        List of product dictionaries
    """
    logger.info(f"Task: Scraping Amazon category - {category_name}")

    try:
        async with AmazonScraper() as scraper:
            products = await scraper.scrape_category(
                category_name=category_name,
                category_url=category_url,
                max_products=max_products
            )

        logger.info(f"Task complete: Scraped {len(products)} products from {category_name}")
        return products

    except Exception as e:
        logger.error(f"Task failed: Error scraping {category_name}: {e}")
        raise


@task(
    name="scrape-all-amazon-categories",
    description="Scrape all configured Amazon categories",
    retries=2,
    retry_delay_seconds=120,
    timeout_seconds=900,
    log_prints=True
)
async def scrape_all_amazon_categories_task() -> Dict[str, List[Dict[str, Any]]]:
    """
    Scrape all Amazon categories defined in settings

    Returns:
        Dictionary mapping category names to product lists
    """
    logger.info("Task: Scraping all Amazon categories")

    try:
        async with AmazonScraper() as scraper:
            results = await scraper.scrape_all_categories()

        total_products = sum(len(products) for products in results.values())
        logger.info(f"Task complete: Scraped {total_products} total products from {len(results)} categories")

        return results

    except Exception as e:
        logger.error(f"Task failed: Error scraping all categories: {e}")
        raise


@task(
    name="filter-brand-products",
    description="Filter products by brand keywords",
    log_prints=True
)
def filter_brand_products_task(
    products: List[Dict[str, Any]],
    brand_keywords: List[str]
) -> List[Dict[str, Any]]:
    """
    Filter products that match brand keywords

    Args:
        products: List of all products
        brand_keywords: List of keywords to match (case-insensitive)

    Returns:
        Filtered list of products
    """
    logger.info(f"Task: Filtering products for brands: {brand_keywords}")

    filtered = []
    keywords_lower = [kw.lower() for kw in brand_keywords]

    for product in products:
        product_name = product.get('product_name', '').lower()

        # Check if any keyword matches
        if any(keyword in product_name for keyword in keywords_lower):
            filtered.append(product)

    logger.info(f"Task complete: Found {len(filtered)} products matching brand keywords")
    return filtered
