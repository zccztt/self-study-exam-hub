# -*- coding: utf-8 -*-
"""FastAPI application entrypoint."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import router
from backend.config import settings

logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL, logging.INFO),
    format="%(asctime)s %(name)s %(levelname)s %(message)s",
)

app = FastAPI(
    title="自考真题模拟与学习系统",
    description="自学考试备考平台 API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL] if not settings.DEBUG else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")


@app.on_event("startup")
async def _load_ai_providers_from_db() -> None:
    """On startup, if DB has active AI/Search providers, load them into memory pools."""
    try:
        from backend.database import SessionLocal
        from backend.config.ai_config import ai_config

        db = SessionLocal()
        try:
            # Load AI providers
            from backend.services.ai_provider_service import AIProviderService
            ai_svc = AIProviderService(db)
            ai_providers = ai_svc.get_active_providers_for_pool()
            if ai_providers:
                ai_config.load_from_db_providers(ai_providers)

            # Load Search providers
            from backend.services.search_provider_service import SearchProviderService
            from backend.services.search_client import search_client, TavilySource
            search_svc = SearchProviderService(db)
            tavily_sources = search_svc.get_tavily_sources()
            if tavily_sources:
                search_client.tavily_sources = [
                    TavilySource(url=s["url"], key=s["key"], name=s.get("name", ""))
                    for s in tavily_sources
                ]
            search_api = search_svc.get_search_api_config()
            if search_api:
                search_client.search_api_url = search_api["url"]
                search_client.search_api_key = search_api["key"]
        finally:
            db.close()
    except Exception:
        logging.getLogger(__name__).debug("DB providers not loaded (table may not exist yet)", exc_info=True)


@app.get("/")
async def root():
    return {
        "message": "自考真题模拟与学习系统 API",
        "version": "0.1.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
