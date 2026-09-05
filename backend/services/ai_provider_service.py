# -*- coding: utf-8 -*-
"""AI provider management service: CRUD, connectivity test, DB↔AIConfig bridge."""

from __future__ import annotations

import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.ai_provider import AIProvider
from backend.utils.crypto import decrypt_api_key, encrypt_api_key, sanitize_error

logger = logging.getLogger(__name__)


class AIProviderService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_providers(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        query = self.db.query(AIProvider)
        if not include_inactive:
            query = query.filter(AIProvider.is_active.is_(True))
        rows = query.order_by(AIProvider.priority.desc(), AIProvider.id.asc()).all()
        return [self._serialize(row, mask_key=True) for row in rows]

    def get_provider(self, provider_id: int) -> Dict[str, Any]:
        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")
        return self._serialize(row, mask_key=True)

    def create_provider(
        self,
        *,
        name: str,
        base_url: str,
        model: str,
        api_key: str,
        timeout: int = 30,
        weight: int = 1,
        roles: Optional[List[str]] = None,
        priority: int = 0,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        existing = self.db.query(AIProvider).filter(AIProvider.name == name).first()
        if existing:
            raise ValueError(f"名称 '{name}' 已存在")

        row = AIProvider(
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            model=model.strip(),
            encrypted_api_key=encrypt_api_key(api_key.strip()),
            timeout=max(3, min(300, timeout)),
            weight=max(1, min(10, weight)),
            roles=roles or [],
            priority=priority,
            description=description,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        logger.info("Created AI provider: %s (model=%s)", row.name, row.model)
        return self._serialize(row, mask_key=True)

    def update_provider(
        self,
        provider_id: int,
        *,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        weight: Optional[int] = None,
        roles: Optional[List[str]] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")

        if name is not None:
            existing = (
                self.db.query(AIProvider)
                .filter(AIProvider.name == name.strip(), AIProvider.id != provider_id)
                .first()
            )
            if existing:
                raise ValueError(f"名称 '{name}' 已被其他服务商使用")
            row.name = name.strip()
        if base_url is not None:
            row.base_url = base_url.strip().rstrip("/")
        if model is not None:
            row.model = model.strip()
        if api_key is not None:
            row.encrypted_api_key = encrypt_api_key(api_key.strip())
        if timeout is not None:
            row.timeout = max(3, min(300, timeout))
        if weight is not None:
            row.weight = max(1, min(10, weight))
        if roles is not None:
            row.roles = roles
        if priority is not None:
            row.priority = priority
        if description is not None:
            row.description = description
        if is_active is not None:
            row.is_active = is_active

        self.db.commit()
        self.db.refresh(row)
        logger.info("Updated AI provider: %s", row.name)
        return self._serialize(row, mask_key=True)

    def delete_provider(self, provider_id: int) -> None:
        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")
        self.db.delete(row)
        self.db.commit()
        logger.info("Deleted AI provider: %s", row.name)

    # ------------------------------------------------------------------
    # Connectivity test
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_base_url(url: str) -> str:
        """Ensure base_url ends with /v1 for OpenAI-compatible APIs."""
        url = url.rstrip("/")
        if not url.endswith("/v1"):
            url += "/v1"
        return url

    def test_provider(
        self, provider_id: int, custom_prompt: str | None = None, model_override: str | None = None
    ) -> Dict[str, Any]:
        """Send a simple test request to verify connectivity."""
        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")

        api_key = decrypt_api_key(row.encrypted_api_key)
        if not api_key:
            row.last_test_ok = False
            self.db.commit()
            return {"success": False, "error": "API Key 解密失败", "latency_ms": 0, "model": ""}

        try:
            from openai import OpenAI
        except ImportError:
            return {"success": False, "error": "openai 库未安装", "latency_ms": 0, "model": ""}

        base_url = self._normalize_base_url(row.base_url)
        if model_override:
            test_model = model_override
        else:
            models = self._parse_models(row.model)
            test_model = models[0] if models else row.model

        test_content = custom_prompt or "Hi, reply with just 'ok'."
        max_tokens = 50 if custom_prompt else 5

        start = time.perf_counter()
        try:
            client = OpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=min(row.timeout, 15),
            )
            response = client.chat.completions.create(
                model=test_model,
                messages=[{"role": "user", "content": test_content}],
                max_tokens=max_tokens,
                temperature=0,
            )
            latency = round((time.perf_counter() - start) * 1000, 1)
            content = response.choices[0].message.content if response.choices else ""
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = True
            self.db.commit()
            return {"success": True, "reply": content, "latency_ms": latency, "model": test_model}
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 1)
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = False
            self.db.commit()
            return {"success": False, "error": sanitize_error(exc), "latency_ms": latency, "model": test_model}

    def test_provider_batch(
        self, provider_id: int, models: list[str], custom_prompt: str | None = None
    ) -> list[Dict[str, Any]]:
        """Test multiple models concurrently for one provider."""
        import concurrent.futures

        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")

        api_key = decrypt_api_key(row.encrypted_api_key)
        if not api_key:
            return [{"model": m, "success": False, "error": "API Key 解密失败", "latency_ms": 0} for m in models]

        try:
            from openai import OpenAI
        except ImportError:
            return [{"model": m, "success": False, "error": "openai 库未安装", "latency_ms": 0} for m in models]

        base_url = self._normalize_base_url(row.base_url)
        test_content = custom_prompt or "Hi, reply with just 'ok'."
        max_tokens = 50 if custom_prompt else 5

        def _test_one(model_name: str) -> Dict[str, Any]:
            start = time.perf_counter()
            try:
                client = OpenAI(api_key=api_key, base_url=base_url, timeout=min(row.timeout, 15))
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": test_content}],
                    max_tokens=max_tokens,
                    temperature=0,
                )
                latency = round((time.perf_counter() - start) * 1000, 1)
                content = response.choices[0].message.content if response.choices else ""
                return {"model": model_name, "success": True, "reply": content, "latency_ms": latency}
            except Exception as exc:
                latency = round((time.perf_counter() - start) * 1000, 1)
                return {"model": model_name, "success": False, "error": sanitize_error(exc), "latency_ms": latency}

        with concurrent.futures.ThreadPoolExecutor(max_workers=min(len(models), 8)) as pool:
            results = list(pool.map(_test_one, models))

        # Update last_test status based on overall results
        any_ok = any(r["success"] for r in results)
        row.last_test_at = datetime.now(timezone.utc)
        row.last_test_ok = any_ok
        self.db.commit()

        return results

    def fetch_models(self, base_url: str, api_key: str) -> List[str]:
        """Fetch available models from an OpenAI-compatible /models endpoint."""
        url = self._normalize_base_url(base_url)
        try:
            from openai import OpenAI
        except ImportError:
            raise ValueError("openai 库未安装")

        client = OpenAI(api_key=api_key, base_url=url, timeout=15)
        try:
            resp = client.models.list()
            return sorted([m.id for m in resp.data])
        except Exception as exc:
            raise ValueError(f"获取模型列表失败: {sanitize_error(exc)}")

    def fetch_models_by_provider(self, provider_id: int) -> List[str]:
        """Fetch available models using the stored credentials of an existing provider."""
        row = self.db.query(AIProvider).filter(AIProvider.id == provider_id).first()
        if not row:
            raise ValueError("AI 服务商不存在")
        api_key = decrypt_api_key(row.encrypted_api_key)
        if not api_key:
            raise ValueError("API Key 解密失败")
        return self.fetch_models(row.base_url, api_key)

    @staticmethod
    def _parse_models(model_field: str) -> List[str]:
        """Parse model field — supports JSON array or comma-separated string."""
        if not model_field:
            return []
        s = model_field.strip()
        if s.startswith("["):
            try:
                arr = json.loads(s)
                if isinstance(arr, list):
                    return [str(m).strip() for m in arr if str(m).strip()]
            except (json.JSONDecodeError, TypeError):
                pass
        return [m.strip() for m in s.split(",") if m.strip()]

    # ------------------------------------------------------------------
    # Bridge: DB → ai_config format
    # ------------------------------------------------------------------

    def get_active_providers_for_pool(self, role: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return active providers in the same dict format as ai_config.

        This is the bridge that lets AIProviderPool use DB providers
        instead of the static JSON file.
        """
        query = (
            self.db.query(AIProvider)
            .filter(AIProvider.is_active.is_(True))
            .order_by(AIProvider.priority.desc(), AIProvider.id.asc())
        )
        rows = query.all()

        providers = []
        for row in rows:
            api_key = decrypt_api_key(row.encrypted_api_key)
            if not api_key:
                continue
            entry = {
                "name": row.name,
                "api_key": api_key,
                "base_url": self._normalize_base_url(row.base_url),
                "model": row.model,
                "timeout": row.timeout,
                "weight": row.weight,
                "roles": row.roles or [],
            }
            providers.append(entry)

        if role:
            matched = [p for p in providers if not p["roles"] or role in p["roles"]]
            return matched or providers
        return providers

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(row: AIProvider, mask_key: bool = True) -> Dict[str, Any]:
        return {
            "id": row.id,
            "name": row.name,
            "base_url": row.base_url,
            "model": row.model,
            "api_key_preview": _mask_key(decrypt_api_key(row.encrypted_api_key)) if mask_key else None,
            "timeout": row.timeout,
            "weight": row.weight,
            "roles": row.roles or [],
            "is_active": row.is_active,
            "priority": row.priority,
            "description": row.description,
            "last_test_at": row.last_test_at.isoformat() if row.last_test_at else None,
            "last_test_ok": row.last_test_ok,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


def _mask_key(key: Optional[str]) -> str:
    """Show only first 4 and last 4 chars: sk-12...ab34"""
    if not key:
        return "***"
    if len(key) <= 8:
        return key[:2] + "***" + key[-2:]
    return key[:4] + "***" + key[-4:]
