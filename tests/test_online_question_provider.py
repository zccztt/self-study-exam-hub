# -*- coding: utf-8 -*-
"""Tests for the custom Tavily-compatible search endpoint."""

import sys
from types import SimpleNamespace

from backend.services.online_question_provider import OnlineQuestionProvider


class _Settings:
    TAVILY_API_KEY = "test-secret"
    TAVILY_API_URL = "https://search-gateway.example.test/"
    QUESTION_SOURCE_DOMAINS = "example.com"


def test_custom_tavily_url_replaces_sdk_base_url(monkeypatch) -> None:
    captured = {}

    class FakeTavilyClient:
        def __init__(self, api_key, api_base_url=None):
            captured["api_key"] = api_key
            captured["api_base_url"] = api_base_url
            self.base_url = api_base_url or "https://api.tavily.com"

        def search(self, **kwargs):
            captured["base_url"] = self.base_url
            captured["search"] = kwargs
            return {
            "results": [
                {
                    "title": "2026 年自考真题",
                    "url": "https://example.com/questions/1",
                    "content": "真题与答案解析",
                }
            ]
        }

    monkeypatch.setitem(sys.modules, "tavily", SimpleNamespace(TavilyClient=FakeTavilyClient))
    provider = OnlineQuestionProvider(_Settings())

    results = provider._search_tavily(
        "自考真题",
        subject_id=1,
        subject_code="03709",
        subject_name="马克思主义基本原理概论",
        year=2026,
        limit=5,
    )

    assert captured["api_key"] == "test-secret"
    assert captured["api_base_url"] == "https://search-gateway.example.test"
    assert captured["base_url"] == "https://search-gateway.example.test"
    assert captured["search"]["query"] == "自考真题"
    assert captured["search"]["max_results"] == 5
    assert results[0]["source_url"] == "https://example.com/questions/1"


def test_tavily_is_disabled_without_custom_url() -> None:
    class MissingUrlSettings:
        TAVILY_API_KEY = "test-secret"
        TAVILY_API_URL = ""
        QUESTION_SOURCE_DOMAINS = ""

    provider = OnlineQuestionProvider(MissingUrlSettings())

    assert provider._search_tavily(
        "自考真题",
        subject_id=1,
        subject_code="03709",
        subject_name="马克思主义基本原理概论",
        year=2026,
        limit=5,
    ) == []
