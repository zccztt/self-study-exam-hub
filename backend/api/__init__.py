# -*- coding: utf-8 -*-
"""API router registry."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api import analysis, auth, enrollment, exam, feedback, flashcard, past_paper, planner, question, resource, subject, upload, video
from backend.api import exam_calendar  # noqa: reimport after rewrite
from backend.api import admin_crawl
from backend.api import ai_provider
from backend.api import search_provider
from backend.api import user_provider
from backend.database import get_db
from backend.elasticsearch_client import es_client
from backend.minio_client import minio_client

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is running"}


@router.get("/health/ready")
async def readiness_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        ) from exc
    return {
        "status": "ready",
        "database": "ok",
        "elasticsearch": "ok" if es_client.is_available else "unavailable",
        "minio": "ok" if minio_client.is_available else "unavailable",
    }


router.include_router(subject.router)
router.include_router(auth.router)
router.include_router(question.router)
router.include_router(exam.router)
router.include_router(video.router)
router.include_router(analysis.router)
router.include_router(planner.router)
router.include_router(enrollment.router)
router.include_router(past_paper.router)
router.include_router(flashcard.router)
router.include_router(feedback.router)
router.include_router(upload.router)
router.include_router(resource.router)
router.include_router(admin_crawl.router)
router.include_router(ai_provider.router)
router.include_router(search_provider.router)
router.include_router(user_provider.router)
router.include_router(exam_calendar.router)
