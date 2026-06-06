# -*- coding: utf-8 -*-
"""Study planner API routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.analysis_service import AnalysisService
from backend.services.planner_service import PlannerService

router = APIRouter(prefix="/planner", tags=["planner"])


class GeneratePlanRequest(BaseModel):
    user_id: int = 1
    exam_date: datetime
    subjects: List[int]
    daily_hours: float
    preferences: Optional[Dict[str, Any]] = None


class UpdateProgressRequest(BaseModel):
    user_id: int = 1
    completed_tasks: List[Dict[str, Any]]


@router.post("/generate")
async def generate_plan(request: GeneratePlanRequest, db: Session = Depends(get_db)):
    service = PlannerService(db)
    return {
        "code": 0,
        "data": service.generate_study_plan(
            user_id=request.user_id,
            exam_date=request.exam_date,
            subjects=request.subjects,
            daily_hours=request.daily_hours,
            preferences=request.preferences,
        ),
    }


@router.get("/latest/{user_id}")
async def get_latest_plan(user_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": PlannerService(db).get_latest_plan(user_id)}


@router.get("/daily-tasks/{user_id}")
async def get_daily_tasks(
    user_id: int,
    date: Optional[datetime] = None,
    db: Session = Depends(get_db),
):
    return {"code": 0, "data": PlannerService(db).get_daily_tasks(user_id, date or datetime.now())}


@router.get("/weak-points/{user_id}/{subject_id}")
async def get_weak_points(user_id: int, subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": PlannerService(db).identify_weak_points(user_id, subject_id)}


@router.post("/progress")
async def update_progress(request: UpdateProgressRequest, db: Session = Depends(get_db)):
    return {"code": 0, "data": PlannerService(db).update_progress(request.user_id, request.completed_tasks)}


@router.get("/allocation")
async def allocate_time(
    total_days: int = Query(default=30, ge=1),
    daily_hours: float = Query(default=2, ge=0.5),
    user_id: int = Query(default=1, ge=1),
    subject_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
):
    service = PlannerService(db)
    weak_points = service.identify_weak_points(user_id, subject_id) if subject_id else []
    high_freq_points = (
        AnalysisService(db).get_high_frequency_points(subject_id, limit=20) if subject_id else []
    )
    return {
        "code": 0,
        "data": service.allocate_time(
            total_days=total_days,
            daily_hours=daily_hours,
            weak_points=weak_points,
            high_freq_points=high_freq_points,
        ),
    }
