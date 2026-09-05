# -*- coding: utf-8 -*-
"""Base crawler module for self-study exam data extraction.

Provides:
- BaseCrawler: abstract class with HTTP session, retry logic, rate limiting
- CrawlLog model: tracks each crawl run
- Data cleaning utilities
"""

import hashlib
import logging
import random
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Common User-Agent rotation pool
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
]


class CrawlResult:
    """Result container for a single crawl operation."""

    def __init__(self, province_code: str, source: str):
        self.province_code = province_code
        self.source = source
        self.started_at = datetime.now()
        self.finished_at: Optional[datetime] = None
        self.schools_found: int = 0
        self.majors_found: int = 0
        self.courses_found: int = 0
        self.majors_created: int = 0
        self.majors_updated: int = 0
        self.links_created: int = 0
        self.errors: List[str] = []
        self.success: bool = False

    def finish(self, success: bool = True):
        self.finished_at = datetime.now()
        self.success = success

    def summary(self) -> str:
        duration = ""
        if self.finished_at:
            secs = (self.finished_at - self.started_at).total_seconds()
            duration = f" ({secs:.1f}s)"
        status = "OK" if self.success else "FAILED"
        return (
            f"[{status}] {self.source} province={self.province_code}{duration} | "
            f"schools={self.schools_found} majors={self.majors_found}(+{self.majors_created}) "
            f"courses={self.courses_found} links=+{self.links_created} errors={len(self.errors)}"
        )


class BaseCrawler(ABC):
    """Abstract base class for exam data crawlers.

    Subclass and implement:
    - source_name: identifier string
    - crawl_province(province_code): main crawl logic
    """

    # Subclasses set this
    source_name: str = "unknown"
    base_url: str = ""

    def __init__(
        self,
        min_delay: float = 2.0,
        max_delay: float = 5.0,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.max_retries = max_retries
        self.timeout = timeout
        self._client: Optional[httpx.Client] = None
        self._request_count = 0

    @property
    def client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(
                timeout=self.timeout,
                follow_redirects=True,
                headers={
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Accept-Encoding": "gzip, deflate",
                    "Connection": "keep-alive",
                },
            )
        return self._client

    def close(self):
        if self._client and not self._client.is_closed:
            self._client.close()

    def _random_ua(self) -> str:
        return random.choice(USER_AGENTS)

    def _sleep(self):
        delay = random.uniform(self.min_delay, self.max_delay)
        time.sleep(delay)

    def fetch(self, url: str, encoding: str = "utf-8") -> Optional[str]:
        """Fetch a URL with retry logic and rate limiting."""
        for attempt in range(self.max_retries):
            try:
                if self._request_count > 0:
                    self._sleep()

                self._request_count += 1
                response = self.client.get(
                    url,
                    headers={"User-Agent": self._random_ua()},
                )
                response.raise_for_status()

                # Handle encoding
                if encoding:
                    response.encoding = encoding
                return response.text

            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP {e.response.status_code} for {url} (attempt {attempt + 1})")
                if e.response.status_code == 404:
                    return None
                if e.response.status_code == 429:
                    # Rate limited - wait longer
                    time.sleep(random.uniform(10, 30))
                elif attempt == self.max_retries - 1:
                    logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                    return None
            except (httpx.ConnectError, httpx.TimeoutException) as e:
                logger.warning(f"Connection error for {url}: {e} (attempt {attempt + 1})")
                if attempt == self.max_retries - 1:
                    return None
                time.sleep(random.uniform(5, 15))
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}")
                return None

        return None

    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content into BeautifulSoup."""
        return BeautifulSoup(html, "html.parser")

    @abstractmethod
    def crawl_province(self, province_code: str) -> CrawlResult:
        """Crawl all majors and courses for a given province.

        Args:
            province_code: 2-digit province code (e.g. "13" for Hebei)

        Returns:
            CrawlResult with all collected data
        """
        ...

    def crawl_all(self, province_codes: Optional[List[str]] = None) -> List[CrawlResult]:
        """Crawl multiple provinces."""
        codes = province_codes or self.supported_provinces()
        results = []
        for code in codes:
            logger.info(f"Crawling province {code} from {self.source_name}...")
            try:
                result = self.crawl_province(code)
                results.append(result)
                logger.info(result.summary())
            except Exception as e:
                logger.error(f"Error crawling province {code}: {e}")
                r = CrawlResult(code, self.source_name)
                r.errors.append(str(e))
                r.finish(success=False)
                results.append(r)
        self.close()
        return results

    def supported_provinces(self) -> List[str]:
        """Return list of province codes this crawler supports."""
        return []


# ------------------------------------------------------------------
# Data cleaning utilities
# ------------------------------------------------------------------

def clean_course_code(code: str) -> str:
    """Normalize a course code: strip whitespace, zero-pad to 5 digits."""
    code = code.strip()
    # Some sources prefix with province-specific codes, extract the standard 5-digit code
    if len(code) > 5 and code[:5].isdigit():
        return code[:5]
    return code.zfill(5) if code.isdigit() and len(code) < 5 else code


def clean_credits(value: str) -> Optional[float]:
    """Parse credits from string, return None if unparseable."""
    try:
        cleaned = value.strip().replace("\xa0", "")
        if not cleaned:
            return None
        return float(cleaned)
    except (ValueError, AttributeError):
        return None


def normalize_course_type(raw: str) -> str:
    """Normalize course type to: required, elective, additional."""
    raw = raw.strip()
    if raw in ("必考", "必修", "必考课", "统考", "公共基础课", "专业核心课"):
        return "required"
    if raw in ("选考", "选修", "选考课", "推荐选考课"):
        return "elective"
    if raw in ("加考", "加考课"):
        return "additional"
    # Default: if contains key characters
    if "必" in raw or "统" in raw:
        return "required"
    if "选" in raw:
        return "elective"
    if "加" in raw:
        return "additional"
    return "required"


def normalize_level(raw: str) -> str:
    """Normalize level to: bk (本科) or zk (专科)."""
    raw = raw.strip()
    if "本科" in raw or "独立本科" in raw or "专升本" in raw:
        return "bk"
    if "专科" in raw or "基础科" in raw:
        return "zk"
    return "bk"  # default


def content_hash(text: str) -> str:
    """Generate a short content hash for change detection."""
    return hashlib.md5(text.encode()).hexdigest()[:12]
