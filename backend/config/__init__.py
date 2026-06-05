# -*- coding: utf-8 -*-
"""
配置模块
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置"""

    # 应用基础配置
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    # 数据库配置
    DATABASE_URL: str

    # Redis配置
    REDIS_URL: str

    # Elasticsearch配置
    ELASTICSEARCH_URL: str

    # MinIO配置
    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET_NAME: str = "exam-hub"

    # Unity2.ai API配置
    UNITY2_API_KEY: Optional[str] = None
    UNITY2_MODEL: str = "claude-sonnet-4-6"
    UNITY2_BASE_URL: str = "https://api.unity2.ai/v1"

    # JWT配置
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # 前端地址
    FRONTEND_URL: str = "http://localhost:3000"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
