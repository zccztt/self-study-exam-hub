# -*- coding: utf-8 -*-
"""Search provider management service: CRUD, connectivity test, DB→SearchClient bridge."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.ai_provider import SearchProvider
from backend.utils.crypto import decrypt_api_key, encrypt_api_key, sanitize_error

logger = logging.getLogger(__name__)


class SearchProviderService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_providers(self, include_inactive: bool = False) -> List[Dict[str, Any]]:
        query = self.db.query(SearchProvider)
        if not include_inactive:
            query = query.filter(SearchProvider.is_active.is_(True))
        rows = query.order_by(SearchProvider.priority.desc(), SearchProvider.id.asc()).all()
        return [self._serialize(row) for row in rows]

    def get_provider(self, provider_id: int) -> Dict[str, Any]:
        row = self.db.query(SearchProvider).filter(SearchProvider.id == provider_id).first()
        if not row:
            raise ValueError("搜索服务商不存在")
        return self._serialize(row)

    def create_provider(
        self,
        *,
        name: str,
        provider_type: str,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        weight: int = 1,
        priority: int = 0,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        if provider_type not in ("tavily", "search_api", "custom"):
            raise ValueError("类型无效，可选: tavily, search_api, custom")
        existing = self.db.query(SearchProvider).filter(SearchProvider.name == name).first()
        if existing:
            raise ValueError(f"名称 '{name}' 已存在")

        row = SearchProvider(
            name=name.strip(),
            provider_type=provider_type,
            base_url=base_url.strip().rstrip("/"),
            encrypted_api_key=encrypt_api_key(api_key.strip()),
            timeout=max(3, min(300, timeout)),
            weight=max(1, min(10, weight)),
            priority=priority,
            description=description,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        logger.info("Created search provider: %s (%s)", row.name, row.provider_type)
        return self._serialize(row)

    def update_provider(
        self,
        provider_id: int,
        *,
        name: Optional[str] = None,
        provider_type: Optional[str] = None,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        weight: Optional[int] = None,
        priority: Optional[int] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        row = self.db.query(SearchProvider).filter(SearchProvider.id == provider_id).first()
        if not row:
            raise ValueError("搜索服务商不存在")

        if name is not None:
            dup = (
                self.db.query(SearchProvider)
                .filter(SearchProvider.name == name.strip(), SearchProvider.id != provider_id)
                .first()
            )
            if dup:
                raise ValueError(f"名称 '{name}' 已被其他服务商使用")
            row.name = name.strip()
        if provider_type is not None:
            if provider_type not in ("tavily", "search_api", "custom"):
                raise ValueError("类型无效")
            row.provider_type = provider_type
        if base_url is not None:
            row.base_url = base_url.strip().rstrip("/")
        if api_key is not None:
            row.encrypted_api_key = encrypt_api_key(api_key.strip())
        if timeout is not None:
            row.timeout = max(3, min(300, timeout))
        if weight is not None:
            row.weight = max(1, min(10, weight))
        if priority is not None:
            row.priority = priority
        if description is not None:
            row.description = description
        if is_active is not None:
            row.is_active = is_active

        self.db.commit()
        self.db.refresh(row)
        return self._serialize(row)

    def delete_provider(self, provider_id: int) -> None:
        row = self.db.query(SearchProvider).filter(SearchProvider.id == provider_id).first()
        if not row:
            raise ValueError("搜索服务商不存在")
        self.db.delete(row)
        self.db.commit()
        logger.info("Deleted search provider: %s", row.name)

    # ------------------------------------------------------------------
    # Connectivity test
    # ------------------------------------------------------------------

    def test_provider(self, provider_id: int, custom_query: str | None = None) -> Dict[str, Any]:
        row = self.db.query(SearchProvider).filter(SearchProvider.id == provider_id).first()
        if not row:
            raise ValueError("搜索服务商不存在")

        api_key = decrypt_api_key(row.encrypted_api_key)
        if not api_key:
            row.last_test_ok = False
            self.db.commit()
            return {"success": False, "error": "API Key 解密失败", "latency_ms": 0}

        query = custom_query or "test"
        start = time.perf_counter()
        try:
            import httpx

            if row.provider_type == "tavily":
                # Tavily POST /search with minimal query
                r = httpx.post(
                    f"{row.base_url}/search",
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}",
                    },
                    json={
                        "api_key": api_key,
                        "query": query,
                        "max_results": 1,
                    },
                    timeout=min(row.timeout, 15),
                )
            else:
                # Self-hosted / custom: GET /search
                r = httpx.get(
                    f"{row.base_url}/search",
                    params={"q": query, "num": 1},
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=min(row.timeout, 15),
                )

            latency = round((time.perf_counter() - start) * 1000, 1)
            ok = 200 <= r.status_code < 400
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = ok
            self.db.commit()
            return {
                "success": ok,
                "status_code": r.status_code,
                "latency_ms": latency,
                "error": None if ok else f"HTTP {r.status_code}",
            }
        except Exception as exc:
            latency = round((time.perf_counter() - start) * 1000, 1)
            row.last_test_at = datetime.now(timezone.utc)
            row.last_test_ok = False
            self.db.commit()
            return {"success": False, "error": sanitize_error(exc), "latency_ms": latency}

    # ------------------------------------------------------------------
    # Bridge: DB → search_client format
    # ------------------------------------------------------------------

    def get_tavily_sources(self) -> List[Dict[str, str]]:
        """Return active Tavily providers as [{url, key, name}] for MultiSearchClient."""
        rows = (
            self.db.query(SearchProvider)
            .filter(
                SearchProvider.is_active.is_(True),
                SearchProvider.provider_type == "tavily",
            )
            .order_by(SearchProvider.priority.desc(), SearchProvider.id.asc())
            .all()
        )
        sources = []
        for row in rows:
            api_key = decrypt_api_key(row.encrypted_api_key)
            if api_key:
                sources.append({"url": row.base_url, "key": api_key, "name": row.name})
        return sources

    def get_search_api_config(self) -> Optional[Dict[str, str]]:
        """Return the highest-priority active search_api provider."""
        row = (
            self.db.query(SearchProvider)
            .filter(
                SearchProvider.is_active.is_(True),
                SearchProvider.provider_type == "search_api",
            )
            .order_by(SearchProvider.priority.desc())
            .first()
        )
        if not row:
            return None
        api_key = decrypt_api_key(row.encrypted_api_key)
        if not api_key:
            return None
        return {"url": row.base_url, "key": api_key}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _serialize(row: SearchProvider) -> Dict[str, Any]:
        key = decrypt_api_key(row.encrypted_api_key)
        return {
            "id": row.id,
            "name": row.name,
            "provider_type": row.provider_type,
            "base_url": row.base_url,
            "api_key_preview": _mask_key(key),
            "timeout": row.timeout,
            "weight": row.weight,
            "is_active": row.is_active,
            "priority": row.priority,
            "description": row.description,
            "last_test_at": row.last_test_at.isoformat() if row.last_test_at else None,
            "last_test_ok": row.last_test_ok,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


def _mask_key(key: Optional[str]) -> str:
    if not key:
        return "***"
    if len(key) <= 8:
        return key[:2] + "***" + key[-2:]
    return key[:4] + "***" + key[-4:]
