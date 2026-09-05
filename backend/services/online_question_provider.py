# -*- coding: utf-8 -*-
"""Online question-source discovery for live question-bank enrichment."""

from __future__ import annotations

import hashlib
import html
import random as _random
import re
import time
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx


SAVED_ONLINE_SOURCE_PREFIX = "线上题源"
TEMP_ONLINE_SOURCE_PREFIX = "在线临时题源"


class OnlineQuestionProvider:
    """Fetch live question-source results without requiring a search API key."""

    BING_SEARCH_URL = "https://www.bing.com/search"
    SO_SEARCH_URL = "https://www.so.com/s"
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123 Safari/537.36 Edg/123.0",
    ]
    USER_AGENT = USER_AGENTS[0]  # backward compat
    REQUEST_DELAY_RANGE = (0.5, 1.5)  # seconds between requests
    MAX_RETRIES = 3
    MAX_PAGE_RESPONSE_SIZE = 2 * 1024 * 1024
    QUESTION_SOURCE_PATTERN = re.compile(r"(自考|真题|试题|题库|练习题|习题|考试|答案|解析)")
    YEAR_PATTERN = re.compile(r"(?<!\d)(20\d{2})(?!\d)")

    # 默认允许的题源域名白名单
    ALLOWED_DOMAINS: List[str] = [
        "zikao365.com", "examw.com", "233.com", "hqwx.com",
        "educity.cn", "51zikao.com", "zikao.cn", "eol.cn",
        "chsi.com.cn", "neea.edu.cn", "zjzs.net",
        "baidu.com", "zhihu.com", "jianshu.com",
    ]

    def __init__(self, settings=None) -> None:
        """初始化搜索提供者。

        Args:
            settings: 可选的应用配置对象，用于获取 Tavily API URL、key 和额外域名。
                      不传时退化为 Bing RSS + 360 搜索行为。
        """
        self._tavily_api_key: Optional[str] = None
        self._tavily_api_url: Optional[str] = None
        self._extra_domains: List[str] = []

        effective_settings = settings
        if effective_settings is None:
            from backend.config import settings as app_settings

            effective_settings = app_settings

        if effective_settings is not None:
            self._tavily_api_key = (getattr(effective_settings, "TAVILY_API_KEY", None) or "").strip() or None
            self._tavily_api_url = (getattr(effective_settings, "TAVILY_API_URL", None) or "").strip() or None
            extra = getattr(effective_settings, "QUESTION_SOURCE_DOMAINS", "") or ""
            self._extra_domains = [
                d.strip().lower()
                for d in extra.split(",")
                if d.strip()
            ]

    @staticmethod
    def _is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
        """检查 URL 的域名是否在白名单中（含子域名匹配）。

        例如 'www.zikao365.com' 匹配白名单中的 'zikao365.com'。
        """
        try:
            hostname = urllib.parse.urlparse(url).hostname
            if not hostname:
                return False
            hostname = hostname.lower()
            for domain in allowed_domains:
                if hostname == domain or hostname.endswith("." + domain):
                    return True
            return False
        except Exception:
            return False

    def _get_allowed_domains(self) -> List[str]:
        """获取合并后的域名白名单（默认 + 环境变量追加）。"""
        return self.ALLOWED_DOMAINS + self._extra_domains

    def _filter_by_domain(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """过滤搜索结果，只保留白名单域名的结果。"""
        allowed = self._get_allowed_domains()
        return [
            r for r in results
            if self._is_allowed_domain(r.get("source_url", ""), allowed)
        ]

    def search(
        self,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        keyword: Optional[str],
        year: Optional[int] = None,
        limit: int = 8,
    ) -> List[Dict[str, Any]]:
        target_year = self._normalize_year(year)
        queries = self._build_queries(
            subject_code=subject_code,
            subject_name=subject_name,
            keyword=keyword,
            year=target_year,
        )
        if not queries:
            return []

        results: List[Dict[str, Any]] = []
        seen_urls: set = set()
        for query in queries:
            candidates: List[Dict[str, Any]] = []

            # 搜索顺序：自定义 Tavily 兼容接口 → Bing RSS → 360 搜索。
            # URL 或 key 任一缺失时不调用 SDK 默认地址。
            if self._tavily_api_url and self._tavily_api_key:
                candidates = self._search_tavily(
                    query,
                    subject_id=subject_id,
                    subject_code=subject_code,
                    subject_name=subject_name,
                    year=target_year,
                    limit=limit,
                )

            # Tavily 有结果时直接使用，避免为了补满数量继续串行访问 Bing 和 360。
            if candidates:
                candidates = self._filter_by_domain(candidates)
                for candidate in candidates:
                    url = candidate.get("source_url")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)
                    results.append(candidate)
                    if len(results) >= limit:
                        return results
                continue

            if len(candidates) < limit:
                candidates.extend(
                    self._search_bing_rss(
                        query,
                        subject_id=subject_id,
                        subject_code=subject_code,
                        subject_name=subject_name,
                        year=target_year,
                        limit=limit,
                    )
                )

            if len(candidates) < limit:
                candidates.extend(
                    self._search_so_html(
                        query,
                        subject_id=subject_id,
                        subject_code=subject_code,
                        subject_name=subject_name,
                        year=target_year,
                        limit=limit,
                    )
                )

            # 域名白名单过滤
            candidates = self._filter_by_domain(candidates)

            for candidate in candidates:
                url = candidate.get("source_url")
                if not url or url in seen_urls:
                    continue
                seen_urls.add(url)
                results.append(candidate)
                if len(results) >= limit:
                    return results

        return results

    def _search_tavily(
        self,
        query: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        year: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """通过使用自定义 base_url 的 Tavily SDK 搜索题源。"""
        if not self._tavily_api_url or not self._tavily_api_key:
            return []

        try:
            from tavily import TavilyClient  # type: ignore[import-untyped]

            client = TavilyClient(
                api_key=self._tavily_api_key,
                api_base_url=self._tavily_api_url.rstrip("/"),
            )
            response = client.search(
                query=query,
                search_depth="basic",
                max_results=limit,
                include_domains=self._get_allowed_domains(),
            )
        except Exception:
            return []

        items: List[Dict[str, Any]] = []
        results = response.get("results", []) if isinstance(response, dict) else []
        for result in results:
            title = (result.get("title") or "").strip()
            url = (result.get("url") or "").strip()
            snippet = (result.get("content") or "").strip()
            if not title or not url:
                continue

            combined = f"{title} {snippet}"
            if not self.QUESTION_SOURCE_PATTERN.search(combined):
                continue

            items.append(
                {
                    "id": self._stable_negative_id(url),
                    "content": title if not snippet else f"{title}\n{snippet[:220]}",
                    "question_type": "online_resource",
                    "options": [],
                    "difficulty": "medium",
                    "year": self._extract_year(combined, year),
                    "month": None,
                    "frequency": 1,
                    "subject_id": subject_id or 0,
                    "subject_code": subject_code,
                    "subject_name": subject_name,
                    "chapter_id": None,
                    "score": 0,
                    "source": "Tavily 实时搜索",
                    "source_url": url,
                    "is_online": True,
                }
            )
            if len(items) >= limit:
                break
        return items

    def _search_bing_rss(
        self,
        query: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        year: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        response = self._request_with_retry(
            self.BING_SEARCH_URL,
            params={"q": query, "format": "rss", "mkt": "zh-CN", "setlang": "zh-CN"},
        )
        if response is None:
            return []

        return self._parse_rss(
            response.text,
            subject_id=subject_id,
            subject_code=subject_code,
            subject_name=subject_name,
            year=year,
            limit=limit,
        )

    @staticmethod
    def _build_queries(
        *,
        subject_code: Optional[str],
        subject_name: Optional[str],
        keyword: Optional[str],
        year: int,
    ) -> List[str]:
        name = (subject_name or "").strip()
        code = (subject_code or "").strip()
        term = (keyword or "").strip()
        year_text = str(year)
        queries = [
            " ".join(part for part in [name, term, year_text, "自考 真题 试题"] if part),
            " ".join(part for part in [name, year_text, "自考 题库 答案 解析"] if part),
            " ".join(part for part in [term, year_text, "自考 真题 试题"] if part),
            " ".join(part for part in [code, name, year_text, "自考 真题"] if part),
        ]
        return [query for query in dict.fromkeys(queries) if query.strip()]

    def _search_so_html(
        self,
        query: str,
        *,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_name: Optional[str],
        year: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        response = self._request_with_retry(
            self.SO_SEARCH_URL,
            params={"q": query},
        )
        if response is None:
            return []

        items: List[Dict[str, Any]] = []
        seen_urls: set = set()
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
                    "year": self._extract_year(combined, year),
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
        year: int,
        limit: int,
    ) -> List[Dict[str, Any]]:
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return []

        items: List[Dict[str, Any]] = []
        seen_urls: set = set()
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
                    "year": self._extract_year(combined, year),
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

    @staticmethod
    def _normalize_year(value: Optional[int]) -> int:
        try:
            year = int(value) if value is not None else datetime.now().year
        except (TypeError, ValueError):
            year = datetime.now().year
        return max(2000, min(2100, year))

    @classmethod
    def _extract_year(cls, text: str, default: int) -> int:
        match = cls.YEAR_PATTERN.search(text or "")
        if not match:
            return default
        return cls._normalize_year(int(match.group(1)))

    # ─── Anti-ban: retry, delay, UA rotation ───────────────────────────────

    def _get_random_ua(self) -> str:
        """随机选择 User-Agent 避免被封。"""
        return _random.choice(self.USER_AGENTS)

    def _request_with_retry(
        self,
        url: str,
        *,
        params: Optional[Dict[str, Any]] = None,
        timeout: int = 10,
        max_response_size: Optional[int] = None,
    ) -> Optional[httpx.Response]:
        """带指数退避重试和随机延迟的 HTTP GET 请求。"""
        for attempt in range(self.MAX_RETRIES):
            if attempt > 0:
                backoff = (2 ** attempt) + _random.uniform(0, 1)
                time.sleep(backoff)
            else:
                # 首次请求也加随机延迟防止突发
                time.sleep(_random.uniform(*self.REQUEST_DELAY_RANGE))

            try:
                request_kwargs = {
                    "params": params,
                    "headers": {"User-Agent": self._get_random_ua()},
                    "timeout": timeout,
                    "follow_redirects": True,
                }
                if max_response_size is None:
                    response = httpx.get(url, **request_kwargs)
                    response.raise_for_status()
                    return response

                with httpx.stream("GET", url, **request_kwargs) as streamed_response:
                    streamed_response.raise_for_status()
                    content = bytearray()
                    for chunk in streamed_response.iter_bytes():
                        remaining = max_response_size - len(content)
                        if remaining <= 0:
                            break
                        content.extend(chunk[:remaining])
                        if len(chunk) >= remaining:
                            break
                    return httpx.Response(
                        status_code=streamed_response.status_code,
                        headers=streamed_response.headers,
                        content=bytes(content),
                        request=streamed_response.request,
                    )
            except httpx.HTTPError:
                continue
        return None

    # ─── Page content extraction ───────────────────────────────────────────

    # 题目提取正则
    _QUESTION_BLOCK_RE = re.compile(
        r'(?:^|\n)\s*(?:第?\s*\d+\s*[题.|、]|\d+[.、)）]|[一二三四五六七八九十]+[、.])\s*(.+?)'
        r'(?=(?:^|\n)\s*(?:第?\s*\d+\s*[题.|、]|\d+[.、)）]|[一二三四五六七八九十]+[、.])|\Z)',
        re.DOTALL,
    )
    _OPTIONS_RE = re.compile(r'[A-D][.、)）]\s*(.+?)(?=[A-D][.、)）]|$)', re.DOTALL)
    _ANSWER_RE = re.compile(r'(?:答案|正确答案|【答案】)[：:]*\s*([A-D]+|.{1,200})', re.IGNORECASE)
    _EXPLANATION_RE = re.compile(r'(?:解析|【解析】|详解)[：:]*\s*(.+?)(?=\n\s*(?:第?\s*\d+|[一二三四五])|\Z)', re.DOTALL)

    def fetch_page_questions(
        self,
        url: str,
        *,
        subject_id: Optional[int] = None,
        subject_code: Optional[str] = None,
        subject_name: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """抓取白名单页面内容，提取结构化真题数据。"""
        allowed = self._get_allowed_domains()
        if not self._is_allowed_domain(url, allowed):
            return []

        response = self._request_with_retry(
            url,
            timeout=12,
            max_response_size=self.MAX_PAGE_RESPONSE_SIZE,
        )
        if response is None:
            return []

        text = self._clean_text(response.text)
        if len(text) < 50:
            return []

        questions: List[Dict[str, Any]] = []
        blocks = self._QUESTION_BLOCK_RE.findall(text)

        for block in blocks[:limit]:
            block = block.strip()
            if len(block) < 10:
                continue

            # 提取选项
            options_matches = self._OPTIONS_RE.findall(block)
            options = [opt.strip() for opt in options_matches] if options_matches else []

            # 提取答案
            answer_match = self._ANSWER_RE.search(block)
            answer = answer_match.group(1).strip() if answer_match else ""

            # 提取解析
            explanation_match = self._EXPLANATION_RE.search(block)
            explanation = explanation_match.group(1).strip() if explanation_match else ""

            # 题干（去掉选项、答案、解析部分）
            content = block
            for pattern in [self._OPTIONS_RE, self._ANSWER_RE, self._EXPLANATION_RE]:
                content = pattern.sub('', content)
            content = content.strip()

            if not content or len(content) < 5:
                continue

            # 判断题型
            if options and len(options) >= 3:
                q_type = "single_choice" if len(answer) <= 1 else "multiple_choice"
            elif "___" in content or "____" in content:
                q_type = "fill_blank"
            else:
                q_type = "short_answer"

            questions.append({
                "id": self._stable_negative_id(f"{url}#{len(questions)}"),
                "content": content,
                "question_type": q_type,
                "options": options[:6],
                "answer": answer,
                "explanation": explanation,
                "difficulty": "medium",
                "year": self._extract_year(block, datetime.now().year),
                "month": None,
                "frequency": 1,
                "subject_id": subject_id or 0,
                "subject_code": subject_code,
                "subject_name": subject_name,
                "chapter_id": None,
                "score": 2 if q_type in ("single_choice", "multiple_choice", "fill_blank") else 6,
                "source": f"页面抓取：{url[:80]}",
                "source_url": url,
                "is_online": True,
                "is_extracted": True,
            })

        return questions
