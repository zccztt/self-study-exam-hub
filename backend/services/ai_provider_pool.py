# -*- coding: utf-8 -*-
"""Weighted AI provider rotation, failover, circuit breaking, and grading consensus."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import statistics
import threading
import time
from typing import Any, Dict, List, Optional

from backend.config.ai_config import ai_config

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

try:
    from openai import AsyncOpenAI
except ImportError:  # pragma: no cover
    AsyncOpenAI = None

try:
    import asyncio
except ImportError:  # pragma: no cover
    asyncio = None


class AIProviderPool:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._cursor = 0
        self._health: Dict[str, Dict[str, float]] = {}

    @property
    def is_configured(self) -> bool:
        return bool(OpenAI is not None and ai_config.is_configured)

    def complete_json(
        self,
        *,
        messages: List[Dict[str, str]],
        role: str,
        temperature: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        providers = self._ordered_providers(role)
        strategy = ai_config.get_strategy()
        max_attempts = min(len(providers), max(1, int(strategy.get("max_attempts", 3))))
        for provider in providers[:max_attempts]:
            result = self._call_provider(provider, messages, temperature)
            if result is not None:
                return result
        return None

    def complete_json_consensus(
        self,
        *,
        messages: List[Dict[str, str]],
        full_score: int,
        temperature: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        strategy = ai_config.get_strategy()
        providers = self._ordered_providers("grading")
        # 仲裁模型通常只声明 judge 角色；将其加入复核候选，但保持名称去重。
        for judge in self._ordered_providers("judge"):
            if judge["name"] not in {item["name"] for item in providers}:
                providers.append(judge)
        review_count = min(len(providers), max(1, int(strategy.get("review_providers", 2))))
        selected = providers[:review_count]
        results: List[Dict[str, Any]] = []
        if len(selected) == 1:
            return self._call_provider(selected[0], messages, temperature)

        with ThreadPoolExecutor(max_workers=len(selected)) as executor:
            futures = {
                executor.submit(self._call_provider, provider, messages, temperature): provider
                for provider in selected
            }
            for future in as_completed(futures):
                result = future.result()
                if isinstance(result, dict) and self._numeric_score(result) is not None:
                    results.append(result)

        if not results:
            return None
        if len(results) == 1:
            return results[0]

        scores = [self._numeric_score(item) or 0.0 for item in results]
        threshold = max(1.0, float(full_score) * float(strategy.get("review_score_difference", 0.1)))
        if max(scores) - min(scores) > threshold and len(providers) > len(selected):
            judge = self._call_provider(providers[len(selected)], messages, temperature)
            if isinstance(judge, dict) and self._numeric_score(judge) is not None:
                results.append(judge)
                scores.append(self._numeric_score(judge) or 0.0)

        median_score = statistics.median(scores)
        chosen = min(
            results,
            key=lambda item: abs((self._numeric_score(item) or 0.0) - median_score),
        )
        chosen = dict(chosen)
        chosen["ai_consensus"] = {
            "review_count": len(results),
            "scores": scores,
            "median_score": median_score,
            "disagreement": max(scores) - min(scores),
        }
        return chosen

    async def async_complete_json(
        self,
        *,
        messages: List[Dict[str, str]],
        role: str,
        temperature: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of complete_json using AsyncOpenAI."""
        providers = self._ordered_providers(role)
        strategy = ai_config.get_strategy()
        max_attempts = min(len(providers), max(1, int(strategy.get("max_attempts", 3))))
        for provider in providers[:max_attempts]:
            result = await self._call_provider_async(provider, messages, temperature)
            if result is not None:
                return result
        return None

    async def async_complete_json_consensus(
        self,
        *,
        messages: List[Dict[str, str]],
        full_score: int,
        temperature: float = 0.0,
    ) -> Optional[Dict[str, Any]]:
        """Async version of complete_json_consensus using asyncio.gather."""
        if asyncio is None:
            return self.complete_json_consensus(
                messages=messages, full_score=full_score, temperature=temperature
            )

        strategy = ai_config.get_strategy()
        providers = self._ordered_providers("grading")
        for judge in self._ordered_providers("judge"):
            if judge["name"] not in {item["name"] for item in providers}:
                providers.append(judge)
        review_count = min(len(providers), max(1, int(strategy.get("review_providers", 2))))
        selected = providers[:review_count]

        if len(selected) == 1:
            return await self._call_provider_async(selected[0], messages, temperature)

        tasks = [
            self._call_provider_async(provider, messages, temperature)
            for provider in selected
        ]
        raw_results = await asyncio.gather(*tasks, return_exceptions=True)
        results: List[Dict[str, Any]] = []
        for result in raw_results:
            if isinstance(result, dict) and self._numeric_score(result) is not None:
                results.append(result)

        if not results:
            return None
        if len(results) == 1:
            return results[0]

        scores = [self._numeric_score(item) or 0.0 for item in results]
        threshold = max(1.0, float(full_score) * float(strategy.get("review_score_difference", 0.1)))
        if max(scores) - min(scores) > threshold and len(providers) > len(selected):
            judge = await self._call_provider_async(providers[len(selected)], messages, temperature)
            if isinstance(judge, dict) and self._numeric_score(judge) is not None:
                results.append(judge)
                scores.append(self._numeric_score(judge) or 0.0)

        median_score = statistics.median(scores)
        chosen = min(
            results,
            key=lambda item: abs((self._numeric_score(item) or 0.0) - median_score),
        )
        chosen = dict(chosen)
        chosen["ai_consensus"] = {
            "review_count": len(results),
            "scores": scores,
            "median_score": median_score,
            "disagreement": max(scores) - min(scores),
        }
        return chosen

    async def _call_provider_async(
        self,
        provider: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> Optional[Dict[str, Any]]:
        """Async version of _call_provider using AsyncOpenAI."""
        if AsyncOpenAI is None:
            # Fallback to sync if AsyncOpenAI is not available
            return self._call_provider(provider, messages, temperature)
        started = time.perf_counter()
        try:
            client = AsyncOpenAI(
                api_key=provider["api_key"],
                base_url=provider["base_url"],
                timeout=provider["timeout"],
            )
            response = await client.chat.completions.create(
                model=provider["model"],
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=messages,
            )
            content = response.choices[0].message.content if response.choices else ""
            parsed = json.loads(content or "{}")
            if not isinstance(parsed, dict):
                raise ValueError("AI response must be a JSON object")
            self._mark_success(provider["name"], started)
            return parsed
        except Exception:
            self._mark_failure(provider["name"])
            return None

    def public_status(self) -> Dict[str, Any]:
        status = ai_config.public_status()
        now = time.time()
        with self._lock:
            health = {
                name: {
                    "failures": int(item.get("failures", 0)),
                    "cooldown": item.get("cooldown_until", 0) > now,
                    "last_latency_ms": round(item.get("last_latency_ms", 0), 1),
                }
                for name, item in self._health.items()
            }
        status["health"] = health
        return status

    def _ordered_providers(self, role: str) -> List[Dict[str, Any]]:
        providers = ai_config.get_providers(role)
        if not providers:
            return []
        weighted: List[Dict[str, Any]] = []
        for provider in providers:
            weighted.extend([provider] * int(provider.get("weight", 1)))
        with self._lock:
            start = self._cursor % len(weighted)
            self._cursor += 1
        ordered_weighted = weighted[start:] + weighted[:start]
        ordered: List[Dict[str, Any]] = []
        seen = set()
        now = time.time()
        for provider in ordered_weighted:
            name = provider["name"]
            if name in seen:
                continue
            seen.add(name)
            state = self._health.get(name, {})
            if state.get("cooldown_until", 0) <= now:
                ordered.append(provider)
        if not ordered:
            ordered = providers
        return ordered

    def _call_provider(
        self,
        provider: Dict[str, Any],
        messages: List[Dict[str, str]],
        temperature: float,
    ) -> Optional[Dict[str, Any]]:
        if OpenAI is None:
            return None
        started = time.perf_counter()
        try:
            client = OpenAI(
                api_key=provider["api_key"],
                base_url=provider["base_url"],
                timeout=provider["timeout"],
            )
            # model 字段可能包含逗号分隔的多个模型名，取第一个
            model_name = provider["model"].split(",")[0].strip()
            response = client.chat.completions.create(
                model=model_name,
                temperature=temperature,
                response_format={"type": "json_object"},
                messages=messages,
            )
            content = response.choices[0].message.content if response.choices else ""
            parsed = json.loads(content or "{}")
            if not isinstance(parsed, dict):
                raise ValueError("AI response must be a JSON object")
            self._mark_success(provider["name"], started)
            return parsed
        except Exception:
            self._mark_failure(provider["name"])
            return None

    def _mark_success(self, name: str, started: float) -> None:
        with self._lock:
            self._health[name] = {
                "failures": 0,
                "cooldown_until": 0,
                "last_latency_ms": (time.perf_counter() - started) * 1000,
            }

    def _mark_failure(self, name: str) -> None:
        strategy = ai_config.get_strategy()
        threshold = max(1, int(strategy.get("failure_threshold", 3)))
        cooldown = max(5, int(strategy.get("cooldown_seconds", 60)))
        with self._lock:
            state = self._health.setdefault(name, {})
            failures = int(state.get("failures", 0)) + 1
            state["failures"] = failures
            if failures >= threshold:
                state["cooldown_until"] = time.time() + cooldown

    @staticmethod
    def _numeric_score(result: Dict[str, Any]) -> Optional[float]:
        try:
            return float(result.get("score"))
        except (TypeError, ValueError):
            return None


ai_provider_pool = AIProviderPool()
