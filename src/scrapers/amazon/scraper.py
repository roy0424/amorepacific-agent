"""
Amazon Best Sellers Scraper using Playwright
"""

import asyncio
from datetime import datetime
from typing import Optional, Dict, List, Any
from decimal import Decimal

from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from loguru import logger

from config.settings import settings
from .anti_bot import AntiBotHelper


class AmazonScraper:
    """Amazon Best Sellers scraper with anti-bot protection"""

    def __init__(self):
        self.settings = settings
        self.anti_bot = AntiBotHelper(self.settings.get_user_agent_list())
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None

    async def __aenter__(self):
        """Async context manager entry"""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()

    async def start(self):
        """Start browser and create context"""
        logger.info("Starting Amazon scraper...")

        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=self.settings.PLAYWRIGHT_HEADLESS,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--disable-dev-shm-usage',
                '--no-sandbox'
            ]
        )

        # Create context with random User-Agent
        user_agent = self.anti_bot.get_random_user_agent()
        self.context = await self.browser.new_context(
            user_agent=user_agent,
            viewport={'width': 1920, 'height': 1080},
            locale='en-US',
            timezone_id='America/New_York'
        )

        # Apply stealth settings
        await self.anti_bot.setup_stealth_context(self.context)

        logger.info(f"Browser started with UA: {user_agent[:50]}...")

    async def close(self):
        """Close browser and context"""
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()
        logger.info("Browser closed")

    async def scrape_category(
        self,
        category_name: str,
        category_url: str,
        max_products: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Scrape a single Amazon Best Sellers category

        Args:
            category_name: Name of the category
            category_url: Best Sellers page URL
            max_products: Maximum number of products to scrape (max 100)

        Returns:
            List of product dictionaries
        """
        logger.info(f"Scraping category: {category_name} (up to {max_products} products)")
        all_products = []

        try:
            page = await self.context.new_page()

            # Calculate number of pages needed (50 products per page)
            pages_needed = min((max_products + 49) // 50, 2)  # Max 2 pages (100 products)

            for page_num in range(1, pages_needed + 1):
                # Construct URL with page parameter
                if page_num == 1:
                    url = category_url
                else:
                    # Add pg parameter for page 2
                    if '?' in category_url:
                        url = f"{category_url}&pg={page_num}"
                    else:
                        url = f"{category_url}?pg={page_num}"

                logger.info(f"Scraping page {page_num}/{pages_needed}...")

                # Navigate to page
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await self.anti_bot.wait_for_page_load(page)

                # Check for blocks/CAPTCHAs
                if await self.anti_bot.check_for_captcha(page):
                    logger.error("CAPTCHA detected - manual intervention required")
                    break

                if await self.anti_bot.check_for_block(page):
                    logger.error("Access blocked by Amazon")
                    break

                # Scroll to bottom to load all lazy-loaded products
                await self.anti_bot.scroll_to_load_all_products(page)

                # Calculate how many products to extract from this page
                products_needed = max_products - len(all_products)
                products_to_extract = min(50, products_needed)

                # Extract products from the page
                products = await self._extract_products_from_page(
                    page,
                    category_name,
                    products_to_extract,
                    start_rank=len(all_products) + 1  # Continue ranking from previous page
                )

                all_products.extend(products)
                logger.info(f"Page {page_num}: Scraped {len(products)} products (total: {len(all_products)})")

                # Stop if we have enough products
                if len(all_products) >= max_products:
                    break

                # Delay between pages
                if page_num < pages_needed:
                    await self.anti_bot.random_delay(
                        self.settings.SCRAPING_DELAY_MIN,
                        self.settings.SCRAPING_DELAY_MAX
                    )

            logger.info(f"Scraped {len(all_products)} products from {category_name}")

            await page.close()

        except Exception as e:
            logger.error(f"Error scraping category {category_name}: {e}")

        return all_products

    async def _extract_products_from_page(
        self,
        page: Page,
        category_name: str,
        max_products: int,
        start_rank: int = 1
    ) -> List[Dict[str, Any]]:
        """
        Extract product information from Best Sellers page

        Args:
            page: Playwright page object
            category_name: Category name
            max_products: Maximum products to extract
            start_rank: Starting rank number (for pagination)
        """
        products = []

        try:
            # Try multiple selector patterns for Amazon Best Sellers
            selector_patterns = [
                'div[id="gridItemRoot"]',
                'div.zg-grid-general-faceout',
                'div[data-asin]',
                'div.a-section.a-spacing-none.aok-relative',
                'div.p13n-sc-uncoverable-faceout'
            ]

            product_items = []
            for selector in selector_patterns:
                try:
                    await page.wait_for_selector(selector, timeout=15000)
                    product_items = await page.query_selector_all(selector)
                    if product_items:
                        break
                except Exception:
                    continue

            if not product_items:
                logger.error("No product items found with any selector pattern")
                return products

            for idx, item in enumerate(product_items[:max_products]):
                try:
                    # Calculate actual rank (start_rank + position on page)
                    actual_rank = start_rank + idx
                    product_data = await self._extract_single_product(item, actual_rank, category_name)
                    if product_data:
                        products.append(product_data)

                    # Random delay between products
                    await self.anti_bot.random_delay(0.1, 0.3)

                except Exception as e:
                    logger.warning(f"Error extracting product at position {idx + 1}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Error extracting products from page: {e}")

        return products

    async def _extract_single_product(
        self,
        element: Any,
        rank: int,
        category_name: str
    ) -> Optional[Dict[str, Any]]:
        """Extract data from a single product element"""
        try:
            # Extract product name
            name_elem = await element.query_selector(
                'div._cDEzb_p13n-sc-css-line-clamp-3_g3dy1, '
                'div[class*="p13n-sc-truncate"]'
            )
            product_name = await name_elem.inner_text() if name_elem else "Unknown"
            product_name = product_name.strip()

            # Extract ASIN from link
            link_elem = await element.query_selector('a[href*="/dp/"]')
            asin = None
            product_url = None
            if link_elem:
                href = await link_elem.get_attribute('href')
                if href:
                    # Extract ASIN from URL (format: /dp/B08XXXX or /product/B08XXXX)
                    import re
                    asin_match = re.search(r'/(?:dp|product)/([A-Z0-9]{10})', href)
                    if asin_match:
                        asin = asin_match.group(1)
                        product_url = f"https://www.amazon.com/dp/{asin}"

            if not asin:
                logger.debug(f"Could not extract ASIN for product at rank {rank}")
                return None

            # Extract price - try multiple selectors and handle different currencies
            price = None
            price_selectors = [
                'span.p13n-sc-price',
                'span._cDEzb_p13n-sc-price_3mJ9Z',
                'span.a-price span.a-offscreen',
                'span.a-price-whole',
                'span[class*="price"]',
                '.a-price .a-offscreen',
                'span[data-a-color="price"]'
            ]

            for selector in price_selectors:
                price_elem = await element.query_selector(selector)
                if price_elem:
                    price_text = await price_elem.inner_text()
                    price_text = price_text.strip()

                    # Handle different currencies (USD, KRW, etc.)
                    # Remove currency symbols and convert to number
                    import re
                    # Remove currency codes (USD, KRW, etc.) and special characters
                    price_text = re.sub(r'[A-Z]{3}\s*', '', price_text)  # Remove currency codes
                    price_text = price_text.replace('$', '').replace('₩', '').replace(',', '').replace('\xa0', '').strip()

                    try:
                        price = Decimal(price_text)
                        break
                    except Exception as e:
                        continue

            # Extract rating - try multiple methods
            rating = None
            import re

            # Method 1: Try to find rating in a link with aria-label (most reliable)
            rating_link = await element.query_selector('a[aria-label*="out of"]')
            if rating_link:
                aria_label = await rating_link.get_attribute('aria-label')
                if aria_label:
                    rating_match = re.search(r'([\d.]+)\s*out of', aria_label)
                    if rating_match:
                        try:
                            rating = Decimal(rating_match.group(1))
                        except:
                            pass

            # Method 2: Try to find rating text in span
            if not rating:
                rating_text_elem = await element.query_selector('span.a-icon-alt')
                if rating_text_elem:
                    rating_text = await rating_text_elem.inner_text()
                    if rating_text:
                        rating_match = re.search(r'([\d.]+)\s*out of', rating_text)
                        if rating_match:
                            try:
                                rating = Decimal(rating_match.group(1))
                            except:
                                pass

            # Method 3: Try class name from star icon
            if not rating:
                rating_icon = await element.query_selector('i[class*="a-icon-star"]')
                if rating_icon:
                    class_name = await rating_icon.get_attribute('class')
                    if class_name:
                        rating_match = re.search(r'a-star-(\d+(?:-\d+)?)', class_name)
                        if rating_match:
                            rating_str = rating_match.group(1).replace('-', '.')
                            try:
                                rating = Decimal(rating_str)
                            except:
                                pass

            # Extract review count
            review_count = None
            review_elem = await element.query_selector(
                'span[class*="a-size-small"] a, span.a-size-small'
            )
            if review_elem:
                review_text = await review_elem.inner_text()
                review_text = review_text.strip().replace(',', '')
                import re
                review_match = re.search(r'(\d+)', review_text)
                if review_match:
                    try:
                        review_count = int(review_match.group(1))
                    except:
                        pass

            # Check if Prime
            is_prime = False
            prime_elem = await element.query_selector('i[class*="prime"]')
            is_prime = prime_elem is not None

            product_data = {
                'asin': asin,
                'product_name': product_name,
                'product_url': product_url,
                'rank': rank,
                'category_name': category_name,
                'price': float(price) if price else None,
                'rating': float(rating) if rating else None,
                'review_count': review_count,
                'is_prime': is_prime,
                'stock_status': 'in_stock',  # Assume in stock if on best sellers
                'collected_at': datetime.now()
            }

            return product_data

        except Exception as e:
            logger.warning(f"Error extracting product data: {e}")
            return None

    async def scrape_all_categories(self, max_products_per_category: int = 100) -> Dict[str, List[Dict[str, Any]]]:
        """
        Scrape all configured Amazon categories

        Args:
            max_products_per_category: Maximum products per category (default 100)

        Returns:
            Dictionary mapping category names to product lists
        """
        logger.info(f"Starting scrape of all categories ({max_products_per_category} products per category)")
        results = {}

        for category_key, category_info in self.settings.AMAZON_CATEGORIES.items():
            try:
                category_name = category_info['name']
                category_url = category_info['url']

                products = await self.scrape_category(
                    category_name=category_name,
                    category_url=category_url,
                    max_products=max_products_per_category
                )

                results[category_name] = products

                # Delay between categories
                await self.anti_bot.random_delay(
                    self.settings.SCRAPING_DELAY_MIN,
                    self.settings.SCRAPING_DELAY_MAX
                )

            except Exception as e:
                logger.error(f"Error scraping category {category_key}: {e}")
                results[category_key] = []

        total_products = sum(len(prods) for prods in results.values())
        logger.info(f"Scraping complete: {total_products} total products from {len(results)} categories")

        return results


async def test_scraper():
    """Test function for the scraper"""
    async with AmazonScraper() as scraper:
        # Test single category
        results = await scraper.scrape_category(
            category_name="Beauty & Personal Care",
            category_url="https://www.amazon.com/Best-Sellers-Beauty/zgbs/beauty",
            max_products=10
        )

        logger.info(f"Test results: {len(results)} products")
        for product in results[:3]:
            logger.info(f"  - {product['rank']}: {product['product_name']}")


if __name__ == "__main__":
    asyncio.run(test_scraper())
