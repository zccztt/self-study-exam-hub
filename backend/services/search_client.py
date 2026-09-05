# -*- coding: utf-8 -*-
"""Multi-source search client.

Supports:
1. Self-hosted search service (SearXNG-compatible):
   - GET /search — default engine search
   - GET /image — image search
   - GET /google/search — specific engine
   - GET /mega/search?engines=bing,google — multi-engine merge
   - GET /extract?url=... — extract webpage content to Markdown

2. Multiple Tavily API instances (different URLs and keys):
   - POST /search — AI-powered web search
   - POST /extract — URL content extraction

Configuration via environment variables:
   SEARCH_API_URL   — self-hosted search base URL
   SEARCH_API_KEY   — self-hosted search API key
   TAVILY_API_URL   — default Tavily proxy URL
   TAVILY_API_KEY   — default Tavily API key
   TAVILY_SOURCES   — JSON array of multiple Tavily instances:
                      [{"url":"...","key":"..."},{"url":"...","key":"..."}]
"""

import json as json_module
import logging
from typing import Any, Dict, List, Optional

import httpx

from backend.config import settings

logger = logging.getLogger(__name__)


class SearchResult:
    """Unified search result."""

    def __init__(self, title: str, url: str, content: str, source: str = ""):
        self.title = title
        self.url = url
        self.content = content
        self.source = source

    def to_dict(self) -> Dict[str, str]:
        return {
            "title": self.title,
            "url": self.url,
            "content": self.content,
            "source": self.source,
        }


class TavilySource:
    """A single Tavily API endpoint."""

    def __init__(self, url: str, key: str, name: str = ""):
        self.url = url.rstrip("/")
        self.key = key
        self.name = name or url

    def _headers(self) -> Dict[str, str]:
        """Build request headers with Bearer auth."""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.key}",
        }

    def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        try:
            payload = {
                "api_key": self.key,
                "query": query,
                "topic": "general",
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": False,
            }
            r = httpx.post(
                f"{self.url}/search",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                return [
                    SearchResult(
                        title=item.get("title", ""),
                        url=item.get("url", ""),
                        content=item.get("content", ""),
                        source=f"tavily:{self.name}",
                    )
                    for item in data.get("results", [])
                ]
            elif r.status_code == 401:
                logger.warning(f"Tavily [{self.name}] auth failed (401): token invalid or expired")
        except Exception as e:
            logger.warning(f"Tavily [{self.name}] search error: {e}")
        return []

    def extract(self, url: str) -> Optional[str]:
        try:
            payload = {"api_key": self.key, "urls": [url]}
            r = httpx.post(
                f"{self.url}/extract",
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json()
                results = data.get("results", [])
                if results:
                    return results[0].get("raw_content") or results[0].get("content", "")
            elif r.status_code == 401:
                logger.warning(f"Tavily [{self.name}] auth failed (401): token invalid or expired")
        except Exception as e:
            logger.warning(f"Tavily [{self.name}] extract error: {e}")
        return None


class MultiSearchClient:
    """Unified multi-source search client."""

    def __init__(
        self,
        search_api_url: Optional[str] = None,
        search_api_key: Optional[str] = None,
        tavily_sources: Optional[List[Dict[str, str]]] = None,
    ):
        self.search_api_url = (search_api_url or getattr(settings, "SEARCH_API_URL", "") or "").rstrip("/")
        self.search_api_key = search_api_key or getattr(settings, "SEARCH_API_KEY", "") or ""
        self.timeout = 30

        # Build Tavily sources list
        self.tavily_sources: List[TavilySource] = []
        if tavily_sources:
            for src in tavily_sources:
                if src.get("url") and src.get("key"):
                    self.tavily_sources.append(TavilySource(
                        url=src["url"], key=src["key"], name=src.get("name", "")
                    ))
        else:
            # Load from settings
            self._load_tavily_from_settings()

    def _load_tavily_from_settings(self):
        """Load Tavily sources from environment config."""
        # First try TAVILY_SOURCES JSON array
        sources_json = getattr(settings, "TAVILY_SOURCES", None)
        if sources_json:
            try:
                parsed = json_module.loads(sources_json)
                if isinstance(parsed, list):
                    for src in parsed:
                        if isinstance(src, dict) and src.get("url") and src.get("key"):
                            self.tavily_sources.append(TavilySource(
                                url=src["url"], key=src["key"], name=src.get("name", "")
                            ))
            except (json_module.JSONDecodeError, TypeError):
                logger.warning("Failed to parse TAVILY_SOURCES JSON")

        # Always add default TAVILY_API_URL/KEY if set and not already in list
        default_url = getattr(settings, "TAVILY_API_URL", "") or ""
        default_key = getattr(settings, "TAVILY_API_KEY", "") or ""
        if default_url and default_key:
            existing_urls = {s.url for s in self.tavily_sources}
            if default_url.rstrip("/") not in existing_urls:
                self.tavily_sources.insert(0, TavilySource(
                    url=default_url, key=default_key, name="default"
                ))

    @property
    def has_search_api(self) -> bool:
        return bool(self.search_api_url and self.search_api_key)

    @property
    def has_tavily(self) -> bool:
        return len(self.tavily_sources) > 0

    @property
    def available_sources(self) -> List[str]:
        sources = []
        if self.has_search_api:
            sources.append("search_api")
        for ts in self.tavily_sources:
            sources.append(f"tavily:{ts.name}")
        return sources

    # ==================================================================
    # Self-hosted Search API
    # ==================================================================

    def _search_api_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.search_api_key}",
            "Content-Type": "application/json",
        }

    def search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using default engine (GET /search)."""
        if self.has_tavily:
            results = self.tavily_search(query, max_results)
            if results:
                return results
        if not self.has_search_api:
            return []
        try:
            r = httpx.get(
                f"{self.search_api_url}/search",
                params={"q": query, "num": max_results},
                headers=self._search_api_headers(),
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return self._parse_search_response(r.json(), "search")
        except Exception as e:
            logger.warning(f"Search API error: {e}")
        return []

    def google_search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search via Google engine (GET /google/search)."""
        if self.has_tavily:
            results = self.tavily_search(query, max_results)
            if results:
                return results
        if not self.has_search_api:
            return []
        try:
            r = httpx.get(
                f"{self.search_api_url}/google/search",
                params={"q": query, "num": max_results},
                headers=self._search_api_headers(),
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return self._parse_search_response(r.json(), "google")
        except Exception as e:
            logger.warning(f"Google search error: {e}")
        return []

    def mega_search(self, query: str, engines: str = "bing,google", max_results: int = 10) -> List[SearchResult]:
        """Multi-engine merged search (GET /mega/search)."""
        if self.has_tavily:
            results = self.tavily_search(query, max_results)
            if results:
                return results
        if not self.has_search_api:
            return []
        try:
            r = httpx.get(
                f"{self.search_api_url}/mega/search",
                params={"q": query, "engines": engines, "num": max_results},
                headers=self._search_api_headers(),
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return self._parse_search_response(r.json(), f"mega:{engines}")
        except Exception as e:
            logger.warning(f"Mega search error: {e}")
        return []

    def image_search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Image search (GET /image)."""
        if not self.has_search_api:
            return []
        try:
            r = httpx.get(
                f"{self.search_api_url}/image",
                params={"q": query, "num": max_results},
                headers=self._search_api_headers(),
                timeout=self.timeout,
            )
            if r.status_code == 200:
                return self._parse_search_response(r.json(), "image")
        except Exception as e:
            logger.warning(f"Image search error: {e}")
        return []

    def extract(self, url: str) -> Optional[str]:
        """Extract webpage content to Markdown."""
        # Prefer the configured Tavily pool. The self-hosted service is kept as
        # a final fallback so a weak local extraction does not hide a fuller
        # Tavily result.
        if self.has_tavily:
            content = self.tavily_extract(url)
            if content:
                return content

        # Fall back to the self-hosted extractor.
        if self.has_search_api:
            try:
                r = httpx.get(
                    f"{self.search_api_url}/extract",
                    params={"url": url},
                    headers=self._search_api_headers(),
                    timeout=self.timeout,
                )
                if r.status_code == 200:
                    data = r.json()
                    content = data.get("content") or data.get("markdown") or data.get("text", "")
                    if content:
                        return content
            except Exception as e:
                logger.warning(f"Extract error: {e}")
        return None

    def _parse_search_response(self, data: Any, source: str) -> List[SearchResult]:
        """Parse self-hosted search API response."""
        results = []
        items = []
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("results", data.get("items", data.get("data", [])))

        for item in items:
            if isinstance(item, dict):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", item.get("link", "")),
                    content=item.get("content", item.get("snippet", item.get("description", ""))),
                    source=source,
                ))
        return results

    # ==================================================================
    # Tavily (multi-source with round-robin failover)
    # ==================================================================

    def tavily_search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search using Tavily sources (tries each until one succeeds)."""
        for source in self.tavily_sources:
            results = source.search(query, max_results)
            if results:
                return results
        return []

    def tavily_extract(self, url: str) -> Optional[str]:
        """Extract using Tavily sources (tries each until one succeeds)."""
        for source in self.tavily_sources:
            content = source.extract(url)
            if content:
                return content
        return None

    def tavily_search_all(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Search ALL Tavily sources and merge results (for broader coverage)."""
        all_results: List[SearchResult] = []
        seen_urls = set()
        for source in self.tavily_sources:
            results = source.search(query, max_results)
            for r in results:
                if r.url not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r.url)
        return all_results

    # ==================================================================
    # Unified search (uses best available source)
    # ==================================================================

    def unified_search(self, query: str, max_results: int = 10) -> List[SearchResult]:
        """Search using all available sources, merge and deduplicate."""
        all_results: List[SearchResult] = []
        seen_urls: set = set()

        # Search every Tavily source first for the broadest independent
        # coverage. The self-hosted service is only used to fill remaining
        # result slots.
        if self.has_tavily:
            tavily_results = self.tavily_search_all(query, max_results)
            for r in tavily_results:
                if r.url not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r.url)

        if len(all_results) < max_results and self.has_search_api:
            results = self.search(query, max_results - len(all_results))
            for r in results:
                if r.url not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(r.url)

        return all_results[:max_results]


# Singleton instance
search_client = MultiSearchClient()
