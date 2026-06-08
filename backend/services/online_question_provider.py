# -*- coding: utf-8 -*-
"""Online question-source discovery for live question-bank enrichment."""

from __future__ import annotations

import hashlib
import html
import re
import urllib.parse
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import httpx


SAVED_ONLINE_SOURCE_PREFIX = "线上题源"
TEMP_ONLINE_SOURCE_PREFIX = "在线临时题源"


class OnlineQuestionProvider:
    """Fetch live question-source results without requiring a search API key."""

    BING_SEARCH_URL = "https://www.bing.com/search"
    SO_SEARCH_URL = "https://www.so.com/s"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
    )
    QUESTION_SOURCE_PATTERN = re.compile(r"(自考|真题|试题|题库|练习题|习题|考试|答案|解析)")

    def search(
        self,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        keyword: Optional[str],
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        queries = self._build_queries(subject_code=subject_code, subject_name=subject_name, keyword=keyword)
        if not queries:
            return []

        results: List[Dict[str, Any]] = []
        seen_urls = set()
        for query in queries:
            candidates = self._search_bing_rss(
                query,
                subject_id=subject_id,
                subject_code=subject_code,
                subject_name=subject_name,
                limit=limit,
            )
            if len(candidates) < limit:
                candidates.extend(
                    self._search_so_html(
                        query,
                        subject_id=subject_id,
                        subject_code=subject_code,
                        subject_name=subject_name,
                        limit=limit,
                    )
                )

            for candidate in candidates:
                url = candidate.get("source_url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(candidate)
                if len(results) >= limit:
                    return results

        return results

    def _search_bing_rss(
        self,
        query: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            response = httpx.get(
                self.BING_SEARCH_URL,
                params={"q": query, "format": "rss", "mkt": "zh-CN", "setlang": "zh-CN"},
                headers={"User-Agent": self.USER_AGENT},
                timeout=8,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        return self._parse_rss(
            response.text,
            subject_id=subject_id,
            subject_code=subject_code,
            subject_name=subject_name,
            limit=limit,
        )

    @staticmethod
    def _build_queries(*, subject_code: Optional[str], subject_name: Optional[str], keyword: Optional[str]) -> List[str]:
        name = (subject_name or "").strip()
        code = (subject_code or "").strip()
        term = (keyword or "").strip()
        queries = [
            " ".join(part for part in [name, term, "自考 真题 试题"] if part),
            " ".join(part for part in [name, "自考 题库 答案 解析"] if part),
            " ".join(part for part in [term, "自考 真题 试题"] if part),
            " ".join(part for part in [code, name, "自考 真题"] if part),
        ]
        return [query for query in dict.fromkeys(queries) if query.strip()]

    def _search_so_html(
        self,
        query: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            response = httpx.get(
                self.SO_SEARCH_URL,
                params={"q": query},
                headers={"User-Agent": self.USER_AGENT},
                timeout=8,
                follow_redirects=True,
            )
            response.raise_for_status()
        except httpx.HTTPError:
            return []

        items: List[Dict[str, Any]] = []
        seen_urls = set()
        for block in re.findall(r'<li[^>]+class="[^"]*res-list[^"]*"[^>]*>.*?</li>', response.text, re.S):
            title_match = re.search(r"<h3[^>]*>.*?</h3>", block, re.S)
            link_match = re.search(r'href="([^"]+)"', block)
            title = self._clean_text(title_match.group(0) if title_match else "")
            link = self._clean_url(link_match.group(1) if link_match else "")
            snippet = self._clean_text(block)
            if not title or not link or link in seen_urls:
                continue

            combined = f"{title} {snippet}"
            if not self.QUESTION_SOURCE_PATTERN.search(combined):
                continue

            seen_urls.add(link)
            items.append(
                {
                    "id": self._stable_negative_id(link),
                    "content": title if not snippet else f"{title}\n{snippet[:220]}",
                    "question_type": "online_resource",
                    "options": [],
                    "difficulty": "medium",
                    "year": 2026,
                    "month": None,
                    "frequency": 1,
                    "subject_id": subject_id or 0,
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "chapter_id": None,
                    "score": 0,
                    "source": "360 搜索实时题源",
                    "source_url": link,
                    "is_online": True,
                }
            )
            if len(items) >= limit:
                break
        return items

    def _parse_rss(
        self,
        xml_text: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        items: List[Dict[str, Any]] = []
        seen_urls = set()
        for item in root.findall(".//item"):
            title = self._clean_text(item.findtext("title"))
            link = self._clean_url(item.findtext("link"))
            snippet = self._clean_text(item.findtext("description"))
            if not title or not link or link in seen_urls:
                continue

            combined = f"{title} {snippet}"
            if not self.QUESTION_SOURCE_PATTERN.search(combined):
                continue

            seen_urls.add(link)
            items.append(
                {
                    "id": self._stable_negative_id(link),
                    "content": title if not snippet else f"{title}\n{snippet}",
                    "question_type": "online_resource",
                    "options": [],
                    "difficulty": "medium",
                    "year": 2026,
                    "month": None,
                    "frequency": 1,
                    "subject_id": subject_id or 0,
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "chapter_id": None,
                    "score": 0,
                    "source": "Bing 实时搜索",
                    "source_url": link,
                    "is_online": True,
                }
            )
            if len(items) >= limit:
                break
        return items

    @staticmethod
    def _clean_text(value: Optional[str]) -> str:
        text = html.unescape(value or "")
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _clean_url(value: Optional[str]) -> str:
        url = html.unescape(value or "").strip()
        if "bing.com/ck/a" in url:
            parsed = urllib.parse.urlparse(url)
            query = urllib.parse.parse_qs(parsed.query)
            for key in ("u", "url"):
                if query.get(key):
                    return query[key][0]
        return url

    @staticmethod
    def _stable_negative_id(value: str) -> int:
        digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
        return -int(digest[:8], 16)
