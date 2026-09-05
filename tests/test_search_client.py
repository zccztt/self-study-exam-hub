"""Tests for Tavily-first multi-source search ordering."""

from types import SimpleNamespace

from backend.services.search_client import MultiSearchClient, SearchResult


def _client() -> MultiSearchClient:
    return MultiSearchClient(
        search_api_url="https://self-hosted.example",
        search_api_key="search-key",
        tavily_sources=[
            {"url": "https://tavily-one.example", "key": "one"},
            {"url": "https://tavily-two.example", "key": "two"},
        ],
    )


def test_unified_search_prefers_tavily_and_uses_self_hosted_as_fallback(monkeypatch) -> None:
    client = _client()
    calls = []

    def tavily_search_all(query: str, max_results: int):
        calls.append(("tavily", query, max_results))
        return [SearchResult("Tavily", "https://example.com/tavily", "", "tavily")]

    def self_hosted_search(query: str, max_results: int):
        calls.append(("self-hosted", query, max_results))
        return [SearchResult("Local", "https://example.com/local", "", "search")]

    monkeypatch.setattr(client, "tavily_search_all", tavily_search_all)
    monkeypatch.setattr(client, "search", self_hosted_search)

    results = client.unified_search("exam", max_results=2)

    assert [result.title for result in results] == ["Tavily", "Local"]
    assert calls == [("tavily", "exam", 2), ("self-hosted", "exam", 1)]


def test_extract_prefers_tavily(monkeypatch) -> None:
    client = _client()
    monkeypatch.setattr(client, "tavily_extract", lambda url: "tavily content")

    def unexpected_self_hosted_call(*args, **kwargs):
        raise AssertionError("self-hosted extraction should only be a fallback")

    monkeypatch.setattr("backend.services.search_client.httpx.get", unexpected_self_hosted_call)

    assert client.extract("https://example.com/paper") == "tavily content"


def test_extract_falls_back_to_self_hosted(monkeypatch) -> None:
    client = _client()
    monkeypatch.setattr(client, "tavily_extract", lambda url: None)
    response = SimpleNamespace(
        status_code=200,
        json=lambda: {"content": "self-hosted content"},
    )
    monkeypatch.setattr("backend.services.search_client.httpx.get", lambda *args, **kwargs: response)

    assert client.extract("https://example.com/paper") == "self-hosted content"


def test_direct_text_search_prefers_tavily(monkeypatch) -> None:
    client = _client()
    calls = []
    monkeypatch.setattr(
        client,
        "tavily_search",
        lambda query, max_results: calls.append("tavily") or [SearchResult("Tavily", "u", "")],
    )
    monkeypatch.setattr(
        "backend.services.search_client.httpx.get",
        lambda *args, **kwargs: calls.append("self-hosted"),
    )

    assert client.search("exam", 3)[0].title == "Tavily"
    assert client.google_search("exam", 3)[0].title == "Tavily"
    assert client.mega_search("exam", max_results=3)[0].title == "Tavily"
    assert calls == ["tavily", "tavily", "tavily"]
