# -*- coding: utf-8 -*-
"""Application settings."""

from typing import Optional

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")
    APP_ENV: str = "development"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./exam_hub.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    ELASTICSEARCH_URL: str = "http://localhost:9200"

    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET_NAME: str = "exam-hub"

    UNITY2_API_KEY: Optional[str] = None
    UNITY2_MODEL: str = "claude-sonnet-4-6"
    UNITY2_BASE_URL: str = "https://api.unity2.ai/v1"

    TAVILY_API_KEY: Optional[str] = None
    TAVILY_API_URL: Optional[str] = None
    TAVILY_SOURCES: Optional[str] = None  # JSON array: [{"url":"...","key":"..."}, ...]
    QUESTION_SOURCE_DOMAINS: str = ""

    # 自建搜索服务配置
    SEARCH_API_URL: Optional[str] = None
    SEARCH_API_KEY: Optional[str] = None

    SECRET_KEY: str = "change-me-in-production"  # 仅开发环境使用，生产环境必须通过 .env 覆盖
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    LOGIN_RATE_LIMIT_PER_MINUTE: int = 10
    PASSWORD_RESET_RATE_LIMIT_PER_MINUTE: int = 3
    EXTERNAL_SEARCH_RATE_LIMIT_PER_MINUTE: int = 20
    AI_RATE_LIMIT_PER_MINUTE: int = 5
    PASSWORD_RESET_EXPIRE_MINUTES: int = 15

    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USERNAME: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_FROM_EMAIL: Optional[str] = None
    SMTP_USE_TLS: bool = True

    FRONTEND_URL: str = "http://localhost:3000"

    @model_validator(mode="after")
    def validate_production_secrets(self):
        weak_secrets = {"change-me-in-production", "your_secret_key_here_change_in_production"}
        if self.APP_ENV.lower() == "production" and (
            self.SECRET_KEY in weak_secrets or len(self.SECRET_KEY) < 32
        ):
            raise ValueError("生产环境必须配置至少32位且非示例值的 SECRET_KEY。")
        return self

settings = Settings()
