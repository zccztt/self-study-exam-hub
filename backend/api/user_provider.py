# -*- coding: utf-8 -*-
"""User-level provider config API routes (authenticated users)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.models.user import User
from backend.services.user_provider_service import UserProviderService

router = APIRouter(prefix="/user/providers", tags=["user-providers"])
logger = logging.getLogger(__name__)


class UserProviderCreate(BaseModel):
    config_type: str = Field(description="ai / search")
    name: str = Field(min_length=1, max_length=100)
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500)
    model: Optional[str] = Field(default=None, max_length=100)
    provider_type: Optional[str] = Field(default=None, description="tavily / search_api / custom")
    timeout: int = Field(default=30, ge=3, le=300)
    description: Optional[str] = Field(default=None, max_length=500)


class UserProviderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=500)
    model: Optional[str] = Field(default=None, max_length=100)
    provider_type: Optional[str] = None
    timeout: Optional[int] = Field(default=None, ge=3, le=300)
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


@router.get("")
async def list_user_providers(
    config_type: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProviderService(db, current_user.id)
    return {"code": 0, "data": svc.list_configs(config_type)}


@router.get("/effective")
async def get_effective_config(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查看当前生效的服务商配置（用户自配 > 管理员全局）"""
    svc = UserProviderService(db, current_user.id)
    ai = svc.get_effective_ai_providers()
    search = svc.get_effective_search_config()
    return {
        "code": 0,
        "data": {
            "ai": {
                "source": ai[0]["source"] if ai else "none",
                "count": len(ai),
                "providers": [
                    {"name": p["name"], "model": p.get("model", ""), "base_url": p["base_url"][:30] + "...", "source": p["source"]}
                    for p in ai
                ],
            },
            "search": {
                "source": search.get("source", "none"),
                "tavily_count": len(search.get("tavily_sources", [])),
                "has_search_api": bool(search.get("search_api")),
            },
        },
    }


@router.get("/{config_id}")
async def get_user_provider(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProviderService(db, current_user.id)
    try:
        return {"code": 0, "data": svc.get_config(config_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_user_provider(
    body: UserProviderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProviderService(db, current_user.id)
    try:
        data = svc.create_config(
            config_type=body.config_type,
            name=body.name,
            base_url=body.base_url,
            api_key=body.api_key,
            model=body.model,
            provider_type=body.provider_type,
            timeout=body.timeout,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.put("/{config_id}")
async def update_user_provider(
    config_id: int,
    body: UserProviderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProviderService(db, current_user.id)
    try:
        data = svc.update_config(
            config_id,
            name=body.name,
            base_url=body.base_url,
            model=body.model,
            provider_type=body.provider_type,
            api_key=body.api_key,
            timeout=body.timeout,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.delete("/{config_id}")
async def delete_user_provider(
    config_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = UserProviderService(db, current_user.id)
    try:
        svc.delete_config(config_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "message": "已删除"}
