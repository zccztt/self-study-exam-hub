# -*- coding: utf-8 -*-
"""API router registry."""

from fastapi import APIRouter

from backend.api import analysis, auth, exam, planner, question, subject, video

router = APIRouter()


@router.get("/health")
async def health_check():
    return {"status": "ok", "message": "Service is running"}


router.include_router(subject.router)
router.include_router(auth.router)
router.include_router(question.router)
router.include_router(exam.router)
router.include_router(video.router)
router.include_router(analysis.router)
router.include_router(planner.router)
