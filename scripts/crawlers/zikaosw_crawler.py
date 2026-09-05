# -*- coding: utf-8 -*-
"""Crawler for zikaosw.cn (自考生网).

URL patterns:
- Province majors list: /zkzy/province-{code}.html
- Individual major plan: /zkzy/major-{id}.html

Extracts:
- Schools per province
- Majors per school (code, name, level)
- Course plan per major (course_code, name, credits, type)

Uses Playwright (headless browser) to bypass JS anti-bot protection.
"""

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from scripts.crawlers import (
    BaseCrawler,
    CrawlResult,
    clean_course_code,
    clean_credits,
    normalize_course_type,
    normalize_level,
)
from scripts.crawlers.browser_crawler import BrowserCrawler

logger = logging.getLogger(__name__)


class ZikaoCourse:
    """Parsed course from a major plan page."""
    def __init__(self, code: str, name: str, credits: Optional[float], course_type: str, sort_order: int):
        self.code = code
        self.name = name
        self.credits = credits
        self.course_type = course_type
        self.sort_order = sort_order

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "name": self.name,
            "credits": self.credits,
            "course_type": self.course_type,
            "sort_order": self.sort_order,
        }


class ZikaoMajor:
    """Parsed major from province listing."""
    def __init__(self, site_id: int, name: str, level: str, school_name: str):
        self.site_id = site_id  # Internal site ID
        self.name = name
        self.level = level
        self.school_name = school_name
        self.code: str = ""  # Filled from detail page
        self.total_credits: Optional[int] = None
        self.courses: List[ZikaoCourse] = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "site_id": self.site_id,
            "code": self.code,
            "name": self.name,
            "level": self.level,
            "school_name": self.school_name,
            "total_credits": self.total_credits,
            "courses": [c.to_dict() for c in self.courses],
        }


class ZikaswCrawler(BaseCrawler):
    """Crawler for zikaosw.cn using Playwright to bypass JS protection."""

    source_name = "zikaosw"
    base_url = "https://www.zikaosw.cn"

    # All province codes supported by the site
    ALL_PROVINCES = [
        "11", "12", "13", "14", "15", "21", "22", "23",
        "31", "32", "33", "34", "35", "36", "37",
        "41", "42", "43", "44", "45", "46",
        "50", "51", "52", "53", "54",
        "61", "62", "63", "64", "65",
    ]

    def __init__(self, headless: bool = True, **kwargs):
        super().__init__(**kwargs)
        self._browser_crawler: Optional[BrowserCrawler] = None
        self._headless = headless

    @property
    def browser(self) -> BrowserCrawler:
        if self._browser_crawler is None:
            self._browser_crawler = BrowserCrawler(
                headless=self._headless,
                min_delay=self.min_delay,
                max_delay=self.max_delay,
            )
        return self._browser_crawler

    def close(self):
        super().close()
        if self._browser_crawler:
            self._browser_crawler.close()
            self._browser_crawler = None

    def supported_provinces(self) -> List[str]:
        return self.ALL_PROVINCES

    def crawl_province(self, province_code: str) -> CrawlResult:
        """Crawl all majors for a province from zikaosw.cn."""
        result = CrawlResult(province_code, self.source_name)

        # Step 1: Fetch province major listing via browser
        url = f"{self.base_url}/zkzy/province-{province_code}.html"
        html = self.browser.fetch(url, wait_selector="a[href*='major-']")
        if not html:
            result.errors.append(f"Failed to fetch province page: {url}")
            result.finish(success=False)
            return result

        # Step 2: Parse school/major links
        majors = self._parse_province_page(html)
        if not majors:
            result.errors.append(f"No majors found on province page: {url}")
            result.finish(success=False)
            return result

        schools = set(m.school_name for m in majors)
        result.schools_found = len(schools)
        result.majors_found = len(majors)
        logger.info(f"  Province {province_code}: found {len(schools)} schools, {len(majors)} majors")

        # Step 3: Fetch each major's detail page for course plans
        for i, major in enumerate(majors):
            logger.debug(f"  Fetching major {i+1}/{len(majors)}: {major.name} (id={major.site_id})")
            detail_url = f"{self.base_url}/zkzy/major-{major.site_id}.html"
            detail_html = self.browser.fetch(detail_url, wait_selector="table")
            if detail_html:
                self._parse_major_detail(major, detail_html)
                result.courses_found += len(major.courses)
            else:
                result.errors.append(f"Failed to fetch major detail: {detail_url}")

        result.finish(success=True)
        return result

    def _parse_province_page(self, html: str) -> List[ZikaoMajor]:
        """Parse the province major listing page.

        Structure: tables grouped by school, each row has major links.
        """
        soup = self.parse_html(html)
        majors = []
        current_school = ""

        # Find the main content area - look for school headers and major links
        # Pattern: school name in header/strong, then major links in rows
        tables = soup.find_all("table")

        for table in tables:
            rows = table.find_all("tr")
            for row in rows:
                # Check if this row is a school header
                th = row.find("th")
                if th:
                    school_text = th.get_text(strip=True)
                    if school_text and ("大学" in school_text or "学院" in school_text):
                        current_school = school_text
                    continue

                # Check first cell for school name (some layouts put school in td)
                cells = row.find_all("td")
                if cells:
                    first_cell_text = cells[0].get_text(strip=True)
                    if ("大学" in first_cell_text or "学院" in first_cell_text) and len(first_cell_text) < 30:
                        current_school = first_cell_text

                # Find major links in this row
                links = row.find_all("a", href=re.compile(r"/zkzy/major-\d+\.html"))
                for link in links:
                    major_id_match = re.search(r"major-(\d+)\.html", link.get("href", ""))
                    if not major_id_match:
                        continue

                    site_id = int(major_id_match.group(1))
                    raw_name = link.get_text(strip=True)

                    # Parse level from name: "工商管理(本科)" or "会计(专科)"
                    level = "bk"
                    name = raw_name
                    level_match = re.search(r"[（(](本科|专科|独立本科|专升本|基础科)[)）]", raw_name)
                    if level_match:
                        level = normalize_level(level_match.group(1))
                        name = re.sub(r"[（(](本科|专科|独立本科|专升本|基础科)[)）]", "", raw_name).strip()

                    # Clean up name: remove "原xxx" suffixes
                    name = re.sub(r"[（(]原[^)）]*[)）]", "", name).strip()

                    majors.append(ZikaoMajor(
                        site_id=site_id,
                        name=name,
                        level=level,
                        school_name=current_school or "未知院校",
                    ))

        # Fallback: if table parsing didn't work, try direct link scanning
        if not majors:
            majors = self._fallback_parse_links(soup)

        return majors

    def _fallback_parse_links(self, soup) -> List[ZikaoMajor]:
        """Fallback parser: scan all major links on the page."""
        majors = []
        links = soup.find_all("a", href=re.compile(r"/zkzy/major-\d+\.html"))
        for link in links:
            major_id_match = re.search(r"major-(\d+)\.html", link.get("href", ""))
            if not major_id_match:
                continue

            site_id = int(major_id_match.group(1))
            raw_name = link.get_text(strip=True)
            if not raw_name or len(raw_name) > 50:
                continue

            level = "bk"
            name = raw_name
            level_match = re.search(r"[（(](本科|专科|独立本科|专升本|基础科)[)）]", raw_name)
            if level_match:
                level = normalize_level(level_match.group(1))
                name = re.sub(r"[（(](本科|专科|独立本科|专升本|基础科)[)）]", "", raw_name).strip()
            name = re.sub(r"[（(]原[^)）]*[)）]", "", name).strip()

            # Try to find school context by looking at parent elements
            school_name = self._find_school_context(link)

            majors.append(ZikaoMajor(
                site_id=site_id,
                name=name,
                level=level,
                school_name=school_name,
            ))

        return majors

    def _find_school_context(self, link_element) -> str:
        """Try to determine school name from surrounding HTML context."""
        # Walk up the DOM tree looking for a school name
        parent = link_element.parent
        for _ in range(5):
            if parent is None:
                break
            prev = parent.find_previous_sibling()
            if prev:
                text = prev.get_text(strip=True)
                if ("大学" in text or "学院" in text) and len(text) < 30:
                    return text
            parent = parent.parent
        return "未知院校"

    def _parse_major_detail(self, major: ZikaoMajor, html: str) -> None:
        """Parse a major detail page to extract course plan."""
        soup = self.parse_html(html)

        # Extract major code from page content
        text = soup.get_text()
        code_match = re.search(r"(?:专业代码|代码)[：:]\s*([A-Z0-9]+)", text)
        if code_match:
            major.code = code_match.group(1).strip()

        # Find the structured course table (has columns: 序号, 课程代码, 课程名称, 学分, 课程类别, 考试方式)
        tables = soup.find_all("table")
        course_table = None
        for table in tables:
            header_row = table.find("tr")
            if not header_row:
                continue
            header_text = header_row.get_text().replace(" ", "").replace("\xa0", "")
            # The right table has both "学分" and "类别" in header
            if "学分" in header_text and "类别" in header_text:
                course_table = table
                break

        if not course_table:
            # Fallback: find table with most 5-digit course codes
            for table in tables:
                table_text = table.get_text()
                codes = re.findall(r"\b\d{5}\b", table_text)
                if len(codes) >= 3:
                    course_table = table
                    break

        if not course_table:
            return

        # Parse course rows
        rows = course_table.find_all("tr")
        if not rows:
            return

        # Detect column layout from header row
        col_map = self._detect_columns(rows[0])
        sort_order = 0
        total_credits = 0

        for row in rows[1:]:  # Skip header
            cells = row.find_all(["td", "th"])
            if len(cells) < 3:
                continue

            cell_texts = [c.get_text(strip=True) for c in cells]

            # Extract fields based on column map
            code = ""
            name = ""
            credits = None
            course_type = "required"

            if col_map:
                code_idx = col_map.get("code", 1)
                name_idx = col_map.get("name", 2)
                credits_idx = col_map.get("credits", 3)
                type_idx = col_map.get("type", 4)

                code = cell_texts[code_idx] if code_idx < len(cell_texts) else ""
                name = cell_texts[name_idx] if name_idx < len(cell_texts) else ""
                credits_str = cell_texts[credits_idx] if credits_idx < len(cell_texts) else ""
                type_str = cell_texts[type_idx] if type_idx < len(cell_texts) else ""
                credits = clean_credits(credits_str)
                course_type = normalize_course_type(type_str) if type_str else "required"
            else:
                # Fallback: positional guess (序号, 代码, 名称, 学分, 类别, ...)
                if len(cell_texts) >= 5:
                    code = cell_texts[1]
                    name = cell_texts[2]
                    credits = clean_credits(cell_texts[3])
                    course_type = normalize_course_type(cell_texts[4])

            # Clean course code: handle "15043/03708" format -> take the standard 5-digit code
            if "/" in code:
                parts = code.split("/")
                # Prefer the part that starts with 0 (standard national code)
                code = next((p.strip() for p in parts if p.strip().startswith("0")), parts[-1].strip())

            code = clean_course_code(code)
            if not code or not re.match(r"^\d{4,5}$", code):
                continue

            # Clean name: remove "（停考）" suffix
            name = re.sub(r"[（(]停考[)）]", "", name).strip()
            if not name or len(name) > 100:
                continue

            sort_order += 1
            if credits:
                total_credits += round(credits)

            major.courses.append(ZikaoCourse(
                code=code,
                name=name,
                credits=credits,
                course_type=course_type,
                sort_order=sort_order,
            ))

        # Set total credits if extracted from table
        if total_credits > 0 and not major.total_credits:
            major.total_credits = total_credits

    def _detect_columns(self, header_row) -> Optional[Dict[str, int]]:
        """Detect column positions from table header row."""
        if not header_row:
            return None

        cells = header_row.find_all(["th", "td"])
        if not cells:
            return None

        col_map = {}
        for i, cell in enumerate(cells):
            text = cell.get_text(strip=True).replace(" ", "").replace("\xa0", "")
            if "代码" in text or "课程代码" in text:
                col_map["code"] = i
            elif "课程名" in text or "名称" in text:
                col_map["name"] = i
            elif "学分" in text:
                col_map["credits"] = i
            elif "类别" in text or "类型" in text:
                col_map["type"] = i

        return col_map if col_map else None
