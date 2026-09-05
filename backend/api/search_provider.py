# -*- coding: utf-8 -*-
"""Search Provider management API routes (admin only)."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.models.user import User
from backend.services.search_provider_service import SearchProviderService

router = APIRouter(prefix="/admin/search-providers", tags=["admin-search"])
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class SearchProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    provider_type: str = Field(description="tavily / search_api / custom")
    base_url: str = Field(min_length=1, max_length=500)
    api_key: str = Field(min_length=1, max_length=500, description="明文传入，服务端加密存储")
    timeout: int = Field(default=30, ge=3, le=300)
    weight: int = Field(default=1, ge=1, le=10)
    priority: int = Field(default=0)
    description: Optional[str] = Field(default=None, max_length=500)


class SearchProviderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    provider_type: Optional[str] = None
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=500)
    timeout: Optional[int] = Field(default=None, ge=3, le=300)
    weight: Optional[int] = Field(default=None, ge=1, le=10)
    priority: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


# ------------------------------------------------------------------
# Auth
# ------------------------------------------------------------------

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可操作搜索服务商配置",
        )
    return current_user


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("")
async def list_search_providers(
    include_inactive: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    return {"code": 0, "data": svc.list_providers(include_inactive=include_inactive)}


@router.get("/{provider_id}")
async def get_search_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    try:
        return {"code": 0, "data": svc.get_provider(provider_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_search_provider(
    body: SearchProviderCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    try:
        data = svc.create_provider(
            name=body.name,
            provider_type=body.provider_type,
            base_url=body.base_url,
            api_key=body.api_key,
            timeout=body.timeout,
            weight=body.weight,
            priority=body.priority,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.put("/{provider_id}")
async def update_search_provider(
    provider_id: int,
    body: SearchProviderUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    try:
        data = svc.update_provider(
            provider_id,
            name=body.name,
            provider_type=body.provider_type,
            base_url=body.base_url,
            api_key=body.api_key,
            timeout=body.timeout,
            weight=body.weight,
            priority=body.priority,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.delete("/{provider_id}")
async def delete_search_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    try:
        svc.delete_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "message": "已删除"}


class TestSearchRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, max_length=500, description="自定义测试搜索词，留空使用默认")


@router.post("/{provider_id}/test")
async def test_search_provider(
    provider_id: int,
    body: TestSearchRequest = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    svc = SearchProviderService(db)
    custom_query = body.prompt if body else None
    try:
        result = svc.test_provider(provider_id, custom_query=custom_query)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "data": result}


@router.post("/reload")
async def reload_search_config(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """从数据库重新加载搜索服务商配置到 MultiSearchClient（无需重启）"""
    from backend.services.search_client import search_client, TavilySource

    svc = SearchProviderService(db)

    # Reload Tavily sources
    tavily_sources = svc.get_tavily_sources()
    search_client.tavily_sources = [
        TavilySource(url=s["url"], key=s["key"], name=s.get("name", ""))
        for s in tavily_sources
    ]

    # Reload search_api config
    search_api = svc.get_search_api_config()
    if search_api:
        search_client.search_api_url = search_api["url"]
        search_client.search_api_key = search_api["key"]

    return {
        "code": 0,
        "data": {
            "tavily_count": len(tavily_sources),
            "search_api": bool(search_api),
            "sources": search_client.available_sources,
        },
    }
