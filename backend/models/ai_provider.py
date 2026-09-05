# -*- coding: utf-8 -*-
"""External service provider models: AI, Search, etc. — encrypted key storage."""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.models import Base


class AIProvider(Base):
    """AI 服务商配置（API Key 加密存储）"""
    __tablename__ = "ai_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="服务商名称，如 openai-main")
    base_url = Column(String(500), nullable=False, comment="API 端点 URL")
    model = Column(String(2000), nullable=False, comment="模型名称，多个以逗号分隔")
    encrypted_api_key = Column(Text, nullable=False, comment="Fernet 加密后的 API Key")
    timeout = Column(Integer, default=30, comment="请求超时(秒)")
    weight = Column(Integer, default=1, comment="轮询权重 1-10")
    roles = Column(JSON, default=list, comment='角色列表: ["analysis","grading","judge",...]')
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级，数值越大越优先")
    description = Column(String(500), nullable=True, comment="备注说明")
    last_test_at = Column(DateTime(timezone=True), nullable=True, comment="最近一次连通测试时间")
    last_test_ok = Column(Boolean, nullable=True, comment="最近测试是否成功")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<AIProvider {self.name} model={self.model}>"


class SearchProvider(Base):
    """搜索服务商配置（Tavily / 自建搜索 / 其他）— API Key 加密存储"""
    __tablename__ = "search_providers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False, index=True, comment="唯一标识，如 tavily-main, searxng-local")
    provider_type = Column(String(50), nullable=False, comment="类型: tavily / search_api / custom")
    base_url = Column(String(500), nullable=False, comment="搜索服务 URL")
    encrypted_api_key = Column(Text, nullable=False, comment="Fernet 加密后的 API Key")
    timeout = Column(Integer, default=30, comment="请求超时(秒)")
    weight = Column(Integer, default=1, comment="轮询权重 1-10")
    is_active = Column(Boolean, default=True, nullable=False, comment="是否启用")
    priority = Column(Integer, default=0, comment="优先级，数值越大越优先")
    description = Column(String(500), nullable=True, comment="备注说明")
    last_test_at = Column(DateTime(timezone=True), nullable=True, comment="最近连通测试时间")
    last_test_ok = Column(Boolean, nullable=True, comment="最近测试是否成功")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<SearchProvider {self.name} type={self.provider_type}>"


class UserProviderConfig(Base):
    """用户个人服务商配置 — 优先于管理员全局配置"""
    __tablename__ = "user_provider_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True, comment="关联用户")
    config_type = Column(String(20), nullable=False, comment="ai / search")
    name = Column(String(100), nullable=False, comment="自定义名称")
    provider_type = Column(String(50), nullable=True, comment="搜索类型: tavily/search_api/custom")
    base_url = Column(String(500), nullable=False)
    model = Column(String(100), nullable=True, comment="AI模型名称")
    encrypted_api_key = Column(Text, nullable=False)
    timeout = Column(Integer, default=30)
    is_active = Column(Boolean, default=True, nullable=False)
    description = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Unique per user+type+name
    __table_args__ = (
        UniqueConstraint('user_id', 'config_type', 'name', name='uq_user_provider_config'),
    )

    def __repr__(self) -> str:
        return f"<UserProviderConfig user={self.user_id} type={self.config_type} name={self.name}>"
