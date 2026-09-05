# -*- coding: utf-8 -*-
"""AI Provider management API routes (admin only)."""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.models.user import User
from backend.services.ai_provider_service import AIProviderService

router = APIRouter(prefix="/admin/ai-providers", tags=["admin-ai"])
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Schemas
# ------------------------------------------------------------------

class AIProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100, description="唯一名称，如 openai-main")
    base_url: str = Field(min_length=1, max_length=500, description="API 端点 URL")
    model: str = Field(min_length=1, max_length=2000, description="模型名称，多个以逗号分隔或 JSON 数组")
    api_key: str = Field(min_length=1, max_length=500, description="API Key（明文传入，服务端加密存储）")
    timeout: int = Field(default=30, ge=3, le=300, description="超时(秒)")
    weight: int = Field(default=1, ge=1, le=10, description="轮询权重")
    roles: Optional[List[str]] = Field(default=None, description='角色: analysis, grading, judge, review, generate')
    priority: int = Field(default=0, description="优先级，越大越优先")
    description: Optional[str] = Field(default=None, max_length=500)


class AIProviderUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    base_url: Optional[str] = Field(default=None, min_length=1, max_length=500)
    model: Optional[str] = Field(default=None, min_length=1, max_length=2000)
    api_key: Optional[str] = Field(default=None, min_length=1, max_length=500)
    timeout: Optional[int] = Field(default=None, ge=3, le=300)
    weight: Optional[int] = Field(default=None, ge=1, le=10)
    roles: Optional[List[str]] = None
    priority: Optional[int] = None
    description: Optional[str] = Field(default=None, max_length=500)
    is_active: Optional[bool] = None


class FetchModelsRequest(BaseModel):
    base_url: Optional[str] = Field(default=None, max_length=500)
    api_key: Optional[str] = Field(default=None, max_length=500)
    provider_id: Optional[int] = Field(default=None, description="已有服务商 ID，使用存储的 key 获取模型")


# ------------------------------------------------------------------
# Auth helpers
# ------------------------------------------------------------------

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅管理员可操作 AI 服务商配置",
        )
    return current_user


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------

@router.get("")
async def list_ai_providers(
    include_inactive: bool = False,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """列出所有 AI 服务商配置（API Key 脱敏展示）"""
    svc = AIProviderService(db)
    return {"code": 0, "data": svc.list_providers(include_inactive=include_inactive)}


@router.get("/{provider_id}")
async def get_ai_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取单个 AI 服务商详情"""
    svc = AIProviderService(db)
    try:
        return {"code": 0, "data": svc.get_provider(provider_id)}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("")
async def create_ai_provider(
    body: AIProviderCreate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """新增 AI 服务商（API Key 自动加密存储）"""
    svc = AIProviderService(db)
    try:
        data = svc.create_provider(
            name=body.name,
            base_url=body.base_url,
            model=body.model,
            api_key=body.api_key,
            timeout=body.timeout,
            weight=body.weight,
            roles=body.roles,
            priority=body.priority,
            description=body.description,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.put("/{provider_id}")
async def update_ai_provider(
    provider_id: int,
    body: AIProviderUpdate,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """更新 AI 服务商配置"""
    svc = AIProviderService(db)
    try:
        data = svc.update_provider(
            provider_id,
            name=body.name,
            base_url=body.base_url,
            model=body.model,
            api_key=body.api_key,
            timeout=body.timeout,
            weight=body.weight,
            roles=body.roles,
            priority=body.priority,
            description=body.description,
            is_active=body.is_active,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}


@router.delete("/{provider_id}")
async def delete_ai_provider(
    provider_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除 AI 服务商"""
    svc = AIProviderService(db)
    try:
        svc.delete_provider(provider_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "message": "已删除"}


class TestProviderRequest(BaseModel):
    prompt: Optional[str] = Field(default=None, max_length=500, description="自定义测试内容，留空使用默认")
    model: Optional[str] = Field(default=None, max_length=200, description="指定测试模型，留空使用第一个")


class BatchTestRequest(BaseModel):
    models: List[str] = Field(min_length=1, description="要测试的模型列表")
    prompt: Optional[str] = Field(default=None, max_length=500, description="自定义测试内容")


@router.post("/{provider_id}/test")
async def test_ai_provider(
    provider_id: int,
    body: TestProviderRequest = None,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """测试 AI 服务商连通性（可指定模型）"""
    svc = AIProviderService(db)
    custom_prompt = body.prompt if body else None
    custom_model = body.model if body else None
    try:
        result = svc.test_provider(provider_id, custom_prompt=custom_prompt, model_override=custom_model)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "data": result}


@router.post("/{provider_id}/test-batch")
async def test_ai_provider_batch(
    provider_id: int,
    body: BatchTestRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """批量并发测试多个模型的连通性"""
    svc = AIProviderService(db)
    try:
        results = svc.test_provider_batch(provider_id, models=body.models, custom_prompt=body.prompt)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "data": results}


@router.post("/fetch-models")
async def fetch_models(
    body: FetchModelsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """根据 base_url 和 api_key 获取可用模型列表，或通过 provider_id 使用已存储的凭据"""
    svc = AIProviderService(db)
    try:
        if body.provider_id:
            models = svc.fetch_models_by_provider(body.provider_id)
        elif body.base_url and body.api_key:
            models = svc.fetch_models(body.base_url, body.api_key)
        else:
            raise ValueError("请提供 base_url + api_key，或 provider_id")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": models}


@router.post("/reload")
async def reload_ai_config(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """从数据库重新加载 AI 服务商配置到内存池（无需重启）"""
    from backend.config.ai_config import ai_config
    svc = AIProviderService(db)
    providers = svc.get_active_providers_for_pool()
    if providers:
        ai_config.load_from_db_providers(providers)
        return {"code": 0, "data": {"loaded": len(providers), "source": "db"}}
    return {"code": 0, "data": {"loaded": 0, "source": ai_config.source, "message": "数据库无可用服务商，保持当前配置"}}


@router.get("/pool-status")
async def ai_pool_status(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取 AI 服务商池运行状态（含健康度、延迟等）"""
    from backend.services.ai_provider_pool import ai_provider_pool
    pool_status = ai_provider_pool.public_status()
    svc = AIProviderService(db)
    db_providers = svc.list_providers(include_inactive=True)
    return {
        "code": 0,
        "data": {
            "pool": pool_status,
            "db_providers": db_providers,
        },
    }
