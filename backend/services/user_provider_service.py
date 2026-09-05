# -*- coding: utf-8 -*-
"""User-level provider config service: CRUD + merged config resolution.

Priority: user's own active config > admin's global active config.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.ai_provider import AIProvider, SearchProvider, UserProviderConfig
from backend.utils.crypto import decrypt_api_key, encrypt_api_key

logger = logging.getLogger(__name__)


class UserProviderService:
    def __init__(self, db: Session, user_id: int):
        self.db = db
        self.user_id = user_id

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    def list_configs(self, config_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = self.db.query(UserProviderConfig).filter(
            UserProviderConfig.user_id == self.user_id,
        )
        if config_type:
            query = query.filter(UserProviderConfig.config_type == config_type)
        rows = query.order_by(UserProviderConfig.id.asc()).all()
        return [self._serialize(row) for row in rows]

    def get_config(self, config_id: int) -> Dict[str, Any]:
        row = self._get_own(config_id)
        return self._serialize(row)

    def create_config(
        self,
        *,
        config_type: str,
        name: str,
        base_url: str,
        api_key: str,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        timeout: int = 30,
        description: Optional[str] = None,
    ) -> Dict[str, Any]:
        if config_type not in ("ai", "search"):
            raise ValueError("config_type 必须是 ai 或 search")
        if config_type == "ai" and not model:
            raise ValueError("AI 类型必须指定 model")
        if config_type == "search" and not provider_type:
            raise ValueError("Search 类型必须指定 provider_type")
        if provider_type and provider_type not in ("tavily", "search_api", "custom"):
            raise ValueError("provider_type 无效")

        existing = (
            self.db.query(UserProviderConfig)
            .filter(
                UserProviderConfig.user_id == self.user_id,
                UserProviderConfig.config_type == config_type,
                UserProviderConfig.name == name.strip(),
            )
            .first()
        )
        if existing:
            raise ValueError(f"名称 '{name}' 在该类型下已存在")

        row = UserProviderConfig(
            user_id=self.user_id,
            config_type=config_type,
            name=name.strip(),
            base_url=base_url.strip().rstrip("/"),
            model=model.strip() if model else None,
            provider_type=provider_type,
            encrypted_api_key=encrypt_api_key(api_key.strip()),
            timeout=max(3, min(300, timeout)),
            description=description,
            is_active=True,
        )
        self.db.add(row)
        self.db.commit()
        self.db.refresh(row)
        return self._serialize(row)

    def update_config(
        self,
        config_id: int,
        *,
        name: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        provider_type: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: Optional[int] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> Dict[str, Any]:
        row = self._get_own(config_id)
        if name is not None:
            dup = (
                self.db.query(UserProviderConfig)
                .filter(
                    UserProviderConfig.user_id == self.user_id,
                    UserProviderConfig.config_type == row.config_type,
                    UserProviderConfig.name == name.strip(),
                    UserProviderConfig.id != config_id,
                )
                .first()
            )
            if dup:
                raise ValueError(f"名称 '{name}' 已存在")
            row.name = name.strip()
        if base_url is not None:
            row.base_url = base_url.strip().rstrip("/")
        if model is not None:
            row.model = model.strip() or None
        if provider_type is not None:
            row.provider_type = provider_type
        if api_key is not None:
            row.encrypted_api_key = encrypt_api_key(api_key.strip())
        if timeout is not None:
            row.timeout = max(3, min(300, timeout))
        if description is not None:
            row.description = description
        if is_active is not None:
            row.is_active = is_active
        self.db.commit()
        self.db.refresh(row)
        return self._serialize(row)

    def delete_config(self, config_id: int) -> None:
        row = self._get_own(config_id)
        self.db.delete(row)
        self.db.commit()

    # ------------------------------------------------------------------
    # Resolution: user config > admin config
    # ------------------------------------------------------------------

    def get_effective_ai_providers(self) -> List[Dict[str, Any]]:
        """Return merged AI provider list: user's own active ones first, then admin's.

        If the user has ANY active AI config, only user's configs are used.
        Otherwise fall back entirely to admin global configs.
        """
        user_rows = (
            self.db.query(UserProviderConfig)
            .filter(
                UserProviderConfig.user_id == self.user_id,
                UserProviderConfig.config_type == "ai",
                UserProviderConfig.is_active.is_(True),
            )
            .all()
        )
        if user_rows:
            providers = []
            for row in user_rows:
                key = decrypt_api_key(row.encrypted_api_key)
                if key:
                    providers.append({
                        "name": row.name,
                        "api_key": key,
                        "base_url": row.base_url,
                        "model": row.model or "",
                        "timeout": row.timeout,
                        "weight": 1,
                        "roles": [],
                        "source": "user",
                    })
            if providers:
                return providers

        # Fall back to admin
        admin_rows = (
            self.db.query(AIProvider)
            .filter(AIProvider.is_active.is_(True))
            .order_by(AIProvider.priority.desc(), AIProvider.id.asc())
            .all()
        )
        providers = []
        for row in admin_rows:
            key = decrypt_api_key(row.encrypted_api_key)
            if key:
                providers.append({
                    "name": row.name,
                    "api_key": key,
                    "base_url": row.base_url,
                    "model": row.model,
                    "timeout": row.timeout,
                    "weight": row.weight,
                    "roles": row.roles or [],
                    "source": "admin",
                })
        return providers

    def get_effective_search_config(self) -> Dict[str, Any]:
        """Return merged search config: user's own active ones first, then admin's.

        Returns dict with 'tavily_sources' and 'search_api' keys.
        If user has any active search configs, only those are used.
        """
        user_rows = (
            self.db.query(UserProviderConfig)
            .filter(
                UserProviderConfig.user_id == self.user_id,
                UserProviderConfig.config_type == "search",
                UserProviderConfig.is_active.is_(True),
            )
            .all()
        )
        if user_rows:
            tavily = []
            search_api = None
            for row in user_rows:
                key = decrypt_api_key(row.encrypted_api_key)
                if not key:
                    continue
                if row.provider_type == "tavily":
                    tavily.append({"url": row.base_url, "key": key, "name": row.name})
                elif row.provider_type in ("search_api", "custom") and not search_api:
                    search_api = {"url": row.base_url, "key": key}
            if tavily or search_api:
                return {"tavily_sources": tavily, "search_api": search_api, "source": "user"}

        # Fall back to admin
        from backend.services.search_provider_service import SearchProviderService
        admin_svc = SearchProviderService(self.db)
        tavily = admin_svc.get_tavily_sources()
        search_api = admin_svc.get_search_api_config()
        return {"tavily_sources": tavily, "search_api": search_api, "source": "admin"}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_own(self, config_id: int) -> UserProviderConfig:
        row = (
            self.db.query(UserProviderConfig)
            .filter(
                UserProviderConfig.id == config_id,
                UserProviderConfig.user_id == self.user_id,
            )
            .first()
        )
        if not row:
            raise ValueError("配置不存在")
        return row

    @staticmethod
    def _serialize(row: UserProviderConfig) -> Dict[str, Any]:
        key = decrypt_api_key(row.encrypted_api_key)
        return {
            "id": row.id,
            "user_id": row.user_id,
            "config_type": row.config_type,
            "name": row.name,
            "provider_type": row.provider_type,
            "base_url": row.base_url,
            "model": row.model,
            "api_key_preview": _mask_key(key),
            "timeout": row.timeout,
            "is_active": row.is_active,
            "description": row.description,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }


def _mask_key(key: Optional[str]) -> str:
    if not key:
        return "***"
    if len(key) <= 8:
        return key[:2] + "***" + key[-2:]
    return key[:4] + "***" + key[-4:]
