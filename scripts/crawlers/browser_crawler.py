# -*- coding: utf-8 -*-
"""Playwright-based browser crawler for sites with JS anti-bot protection.

Handles:
- JavaScript challenge pages (like zikaosw.cn's acw_sc__v2 cookie)
- Dynamic content loading
- Cookie persistence across requests

Usage:
    from scripts.crawlers.browser_crawler import BrowserCrawler
    crawler = BrowserCrawler()
    html = crawler.fetch_with_browser('https://www.zikaosw.cn/zkzy/province-13.html')
"""

import logging
import time
import random
from typing import Optional

try:
    from playwright.sync_api import sync_playwright, Browser, Page, BrowserContext
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

logger = logging.getLogger(__name__)


class BrowserCrawler:
    """Headless browser crawler using Playwright to bypass JS anti-bot."""

    def __init__(
        self,
        headless: bool = True,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        timeout: float = 30000,  # milliseconds
    ):
        if not HAS_PLAYWRIGHT:
            raise RuntimeError(
                "Playwright not installed. Run: pip install playwright && python -m playwright install chromium"
            )
        self.headless = headless
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.timeout = timeout
        self._playwright = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._request_count = 0

    def _ensure_browser(self):
        """Lazily start browser."""
        if self._browser is None:
            self._playwright = sync_playwright().start()
            self._browser = self._playwright.chromium.launch(
                headless=self.headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                ],
            )
            self._context = self._browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                locale="zh-CN",
            )
            # Remove webdriver detection
            self._context.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
                Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
            """)
            self._page = self._context.new_page()
            logger.info("Browser started (headless=%s)", self.headless)

    def _sleep(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def fetch(self, url: str, wait_selector: Optional[str] = None, max_retries: int = 2) -> Optional[str]:
        """Fetch a page using headless browser, handling JS challenges.

        Args:
            url: URL to fetch
            wait_selector: CSS selector to wait for (indicates page is loaded)
            max_retries: Number of retry attempts

        Returns:
            Page HTML content or None on failure
        """
        self._ensure_browser()

        for attempt in range(max_retries + 1):
            try:
                if self._request_count > 0:
                    self._sleep()

                self._request_count += 1
                logger.debug(f"Browser fetching: {url} (attempt {attempt + 1})")

                # Navigate
                response = self._page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")

                if response and response.status == 403:
                    logger.warning(f"403 Forbidden: {url}")
                    if attempt < max_retries:
                        time.sleep(random.uniform(5, 10))
                        continue
                    return None

                if response and response.status == 404:
                    return None

                # Wait for JS challenge to resolve (common pattern: page reloads after setting cookie)
                # Check if the page has actual content or is a JS challenge
                content = self._page.content()
                if self._is_js_challenge(content):
                    logger.info(f"  JS challenge detected, waiting for redirect...")
                    # Wait for navigation (the JS will set a cookie and reload)
                    try:
                        self._page.wait_for_load_state("networkidle", timeout=10000)
                        time.sleep(2)  # Extra wait for cookie to be set
                        # Re-fetch the page (now with cookie)
                        self._page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                        self._page.wait_for_load_state("networkidle", timeout=10000)
                        content = self._page.content()
                    except Exception:
                        # Try once more
                        time.sleep(3)
                        self._page.goto(url, timeout=self.timeout, wait_until="domcontentloaded")
                        time.sleep(2)
                        content = self._page.content()

                # If still a challenge page, retry
                if self._is_js_challenge(content):
                    if attempt < max_retries:
                        logger.warning(f"  Still JS challenge after wait, retrying...")
                        time.sleep(random.uniform(3, 6))
                        continue
                    logger.error(f"  Could not bypass JS challenge for: {url}")
                    return None

                # Wait for specific selector if provided
                if wait_selector:
                    try:
                        self._page.wait_for_selector(wait_selector, timeout=10000)
                        content = self._page.content()
                    except Exception:
                        pass  # Continue with what we have

                logger.debug(f"  Got {len(content)} chars")
                return content

            except Exception as e:
                logger.warning(f"Browser error for {url}: {e} (attempt {attempt + 1})")
                if attempt == max_retries:
                    return None
                time.sleep(random.uniform(3, 8))

        return None

    def _is_js_challenge(self, html: str) -> bool:
        """Detect if the page is a JS anti-bot challenge rather than real content."""
        if not html or len(html) < 200:
            return True
        # Common patterns in JS challenge pages
        challenge_indicators = [
            "var arg1=",
            "acw_sc__v2",
            "_0x",  # Obfuscated JS variable names
            "document.cookie",
        ]
        # Count how many indicators are present
        hits = sum(1 for indicator in challenge_indicators if indicator in html[:5000])
        # If multiple indicators and very little actual content
        if hits >= 2 and "<table" not in html and "<div class" not in html[:2000]:
            return True
        return False

    def close(self):
        """Close browser and cleanup."""
        try:
            if self._page:
                self._page.close()
            if self._context:
                self._context.close()
            if self._browser:
                self._browser.close()
            if self._playwright:
                self._playwright.stop()
        except Exception as e:
            logger.debug(f"Cleanup error: {e}")
        finally:
            self._page = None
            self._context = None
            self._browser = None
            self._playwright = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
