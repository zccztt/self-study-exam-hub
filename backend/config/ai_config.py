# -*- coding: utf-8 -*-
"""Secure single- or multi-provider AI configuration loader.

Priority chain:
  1. DB table `ai_providers` (if any active rows exist) — dynamic, admin-manageable
  2. External JSON file (EXAM_HUB_AI_CONFIG env var) — static, ops-managed
  3. Environment variables (UNITY2_*) — minimal fallback
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class AIConfig:
    """Load AI providers from DB → JSON file → env, with hot-reload from DB."""

    CONFIG_FILE = Path(os.getenv("EXAM_HUB_AI_CONFIG", "D:/wd/.exam_hub/ai_config.json"))

    def __init__(self) -> None:
        self._providers: List[Dict[str, Any]] = []
        self._strategy: Dict[str, Any] = {}
        self._source: str = "none"  # "db", "file", or "env"
        self._load_file_and_env()

    def _load_file_and_env(self) -> None:
        """Load from JSON file + env fallback (original logic)."""
        raw: Dict[str, Any] = {}
        if self.CONFIG_FILE.exists():
            try:
                raw = json.loads(self.CONFIG_FILE.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                logger.warning("Failed to load AI config from %s: %s", self.CONFIG_FILE, exc)

        self._strategy = {
            "timeout": 30,
            "max_attempts": 3,
            "failure_threshold": 3,
            "cooldown_seconds": 60,
            "review_providers": 2,
            "review_score_difference": 0.1,
            **(raw.get("strategy") if isinstance(raw.get("strategy"), dict) else {}),
        }

        providers = raw.get("providers") if isinstance(raw.get("providers"), list) else []
        for index, item in enumerate(providers):
            if not isinstance(item, dict):
                continue
            api_key = item.get("api_key")
            if not api_key and item.get("api_key_env"):
                api_key = os.getenv(str(item["api_key_env"]))
            provider = self._normalize_provider(item, api_key, index)
            if provider:
                self._providers.append(provider)

        if not self._providers:
            api_key = raw.get("api_key") or os.getenv("UNITY2_API_KEY")
            base_url = raw.get("base_url") or os.getenv("UNITY2_BASE_URL", "http://localhost:11434/v1")
            model = raw.get("model") or os.getenv("UNITY2_MODEL", "qwen2.5:14b")
            provider = self._normalize_provider(
                {
                    "name": "default",
                    "base_url": base_url,
                    "model": model,
                    "timeout": raw.get("timeout", self._strategy["timeout"]),
                    "weight": 1,
                    "roles": ["analysis", "generate", "grading", "review", "judge"],
                },
                api_key,
                0,
            )
            if provider:
                self._providers.append(provider)
                self._source = "env"
            else:
                self._source = "none"
        else:
            self._source = "file"

    def load_from_db_providers(self, db_providers: List[Dict[str, Any]]) -> None:
        """Replace in-memory providers with DB-sourced ones.

        Called by the pool or a startup hook when DB providers are available.
        The db_providers list should already have decrypted api_key values.
        """
        if not db_providers:
            return
        self._providers = []
        for idx, item in enumerate(db_providers):
            provider = self._normalize_provider(item, item.get("api_key"), idx)
            if provider:
                self._providers.append(provider)
        if self._providers:
            self._source = "db"
            logger.info("AI config loaded from DB: %d provider(s)", len(self._providers))

    def _normalize_provider(self, item: Dict[str, Any], api_key: Any, index: int) -> Optional[Dict[str, Any]]:
        base_url = str(item.get("base_url") or "").strip()
        model = str(item.get("model") or "").strip()
        key = str(api_key or "").strip()
        if not key or not base_url or not model:
            return None
        roles = item.get("roles") if isinstance(item.get("roles"), list) else []
        return {
            "name": str(item.get("name") or f"provider-{index + 1}"),
            "api_key": key,
            "base_url": base_url.rstrip("/"),
            "model": model,
            "timeout": max(3, int(item.get("timeout", self._strategy.get("timeout", 30)))),
            "weight": max(1, min(10, int(item.get("weight", 1)))),
            "roles": [str(role) for role in roles],
        }

    @property
    def is_configured(self) -> bool:
        return bool(self._providers)

    @property
    def source(self) -> str:
        return self._source

    def get_config(self) -> Optional[Dict[str, Any]]:
        """Backward-compatible first-provider accessor."""
        return dict(self._providers[0]) if self._providers else None

    def get_providers(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        providers = self._providers
        if role:
            matched = [item for item in providers if not item["roles"] or role in item["roles"]]
            providers = matched or providers
        return [dict(item) for item in providers]

    def get_strategy(self) -> Dict[str, Any]:
        return dict(self._strategy)

    def public_status(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "source": self._source,
            "provider_count": len(self._providers),
            "providers": [
                {
                    "name": item["name"],
                    "model": item["model"],
                    "roles": item["roles"],
                    "weight": item["weight"],
                }
                for item in self._providers
            ],
            "strategy": self.get_strategy(),
        }


ai_config = AIConfig()
