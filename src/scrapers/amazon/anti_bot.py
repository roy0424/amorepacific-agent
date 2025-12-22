"""
Anti-bot detection utilities for Amazon scraping
"""

import random
import asyncio
from typing import Any
from playwright.async_api import Page, BrowserContext
from loguru import logger


# Common User-Agent strings
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]


def get_random_user_agent() -> str:
    """
    Get a random User-Agent string

    Returns:
        Random User-Agent string
    """
    return random.choice(USER_AGENTS)


class AntiBotHelper:
    """Utilities to avoid bot detection"""

    def __init__(self, user_agents: list[str]):
        self.user_agents = user_agents

    def get_random_user_agent(self) -> str:
        """Get a random User-Agent from the pool"""
        return random.choice(self.user_agents)

    async def random_delay(self, min_seconds: float = 1.0, max_seconds: float = 3.0):
        """Add random delay between requests"""
        delay = random.uniform(min_seconds, max_seconds)
        await asyncio.sleep(delay)

    async def setup_stealth_context(self, context: BrowserContext):
        """Setup stealth settings to avoid detection"""
        # Remove webdriver property
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
        """)

        # Override plugins to make browser look real
        await context.add_init_script("""
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
        """)

        # Override languages
        await context.add_init_script("""
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
        """)

    async def check_for_captcha(self, page: Page) -> bool:
        """Check if CAPTCHA page is displayed"""
        try:
            captcha_selectors = [
                'input[id*="captcha"]',
                'div[id*="captcha"]',
                'img[src*="captcha"]',
                'form[action*="validateCaptcha"]'
            ]

            for selector in captcha_selectors:
                element = await page.query_selector(selector)
                if element:
                    logger.warning("CAPTCHA detected!")
                    return True

            # Check page title
            title = await page.title()
            if "Robot Check" in title or "CAPTCHA" in title:
                logger.warning(f"CAPTCHA detected in title: {title}")
                return True

            return False

        except Exception as e:
            logger.error(f"Error checking for CAPTCHA: {e}")
            return False

    async def check_for_block(self, page: Page) -> bool:
        """Check if we're blocked or rate-limited"""
        try:
            content = await page.content()

            block_indicators = [
                "To discuss automated access to Amazon data",
                "Sorry, we just need to make sure you're not a robot",
                "Enter the characters you see below",
                "503 Service Temporarily Unavailable"
            ]

            for indicator in block_indicators:
                if indicator in content:
                    logger.warning(f"Block detected: {indicator}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error checking for block: {e}")
            return False

    async def wait_for_page_load(self, page: Page, timeout: int = 30000):
        """Wait for page to fully load with network idle"""
        try:
            await page.wait_for_load_state("networkidle", timeout=timeout)
            await self.random_delay(0.5, 1.5)
        except Exception as e:
            logger.warning(f"Page load timeout: {e}")

    async def scroll_page_randomly(self, page: Page):
        """Scroll page randomly to simulate human behavior"""
        try:
            # Get page height
            height = await page.evaluate("document.body.scrollHeight")

            # Skip scrolling if page is too small
            if height < 200:
                return

            # Random scroll to middle
            max_scroll = min(height // 2, 1000)
            scroll_to = random.randint(100, max(150, max_scroll))
            await page.evaluate(f"window.scrollTo(0, {scroll_to})")
            await self.random_delay(0.3, 0.8)

            # Scroll back up a bit
            scroll_to = random.randint(0, max(1, scroll_to // 2))
            await page.evaluate(f"window.scrollTo(0, {scroll_to})")
            await self.random_delay(0.2, 0.5)

        except Exception as e:
            logger.warning(f"Error scrolling page: {e}")

    async def scroll_to_load_all_products(self, page: Page):
        """Scroll to bottom of page to load all lazy-loaded products"""
        try:
            # Get initial height
            last_height = await page.evaluate("document.body.scrollHeight")

            # Scroll down multiple times to trigger lazy loading
            for i in range(5):  # Max 5 scrolls
                # Scroll to bottom
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")

                # Wait for new content to load
                await self.random_delay(1.0, 2.0)

                # Calculate new height
                new_height = await page.evaluate("document.body.scrollHeight")

                # If height hasn't changed, we've reached the end
                if new_height == last_height:
                    break

                last_height = new_height

            # Scroll back to top
            await page.evaluate("window.scrollTo(0, 0)")
            await self.random_delay(0.5, 1.0)

        except Exception as e:
            logger.warning(f"Error scrolling to load products: {e}")
