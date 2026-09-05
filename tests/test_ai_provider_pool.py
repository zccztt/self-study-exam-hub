# -*- coding: utf-8 -*-
"""Tests for multi-provider configuration and consensus behavior."""

from types import SimpleNamespace

from backend.services.ai_provider_pool import AIProviderPool


def test_consensus_uses_median_and_judge(monkeypatch) -> None:
    pool = AIProviderPool()
    providers = [
        {"name": "a", "weight": 1},
        {"name": "b", "weight": 1},
        {"name": "judge", "weight": 1},
    ]
    monkeypatch.setattr(pool, "_ordered_providers", lambda role: providers)
    responses = iter([{"score": 2}, {"score": 8}, {"score": 5}])
    monkeypatch.setattr(pool, "_call_provider", lambda provider, messages, temperature: next(responses))
    monkeypatch.setattr(
        "backend.services.ai_provider_pool.ai_config.get_strategy",
        lambda: {"review_providers": 2, "review_score_difference": 0.1},
    )

    result = pool.complete_json_consensus(messages=[], full_score=10)

    assert result is not None
    assert result["score"] == 5
    assert result["ai_consensus"]["review_count"] == 3


def test_public_status_does_not_expose_keys(monkeypatch) -> None:
    monkeypatch.setattr(
        "backend.services.ai_provider_pool.ai_config.public_status",
        lambda: {
            "configured": True,
            "provider_count": 1,
            "providers": [{"name": "safe", "model": "m", "roles": [], "weight": 1}],
            "strategy": {},
        },
    )
    status = AIProviderPool().public_status()
    assert "api_key" not in str(status).lower()
    assert "base_url" not in str(status).lower()
