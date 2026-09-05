# -*- coding: utf-8 -*-
"""Study planner API routes."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.dependencies import get_current_user, require_self
from backend.models.subject import Subject
from backend.models.user import User
from backend.services.analysis_service import AnalysisService
from backend.services.enrollment_service import EnrollmentService
from backend.services.planner_service import PlannerService

router = APIRouter(prefix="/planner", tags=["planner"])


class GeneratePlanRequest(BaseModel):
    user_id: int = 1
    exam_date: datetime
    subjects: Optional[List[int]] = Field(default=None, max_length=10)
    daily_hours: float = Field(ge=0.5, le=12)
    preferences: Optional[Dict[str, Any]] = None
    enrollment_id: Optional[int] = None  # 如果提供，自动从报考记录获取待考科目
    user_context: Optional[str] = Field(default=None, max_length=2000, description="用户个人情况描述，如学习基础、可用时间、目标等")

    @field_validator("exam_date")
    @classmethod
    def validate_exam_date(cls, value: datetime) -> datetime:
        if value.date() <= datetime.now().date():
            raise ValueError("考试日期必须晚于今天。")
        return value

    @field_validator("subjects")
    @classmethod
    def validate_subjects(cls, value: Optional[List[int]]) -> Optional[List[int]]:
        if value is not None and len(set(value)) != len(value):
            raise ValueError("subjects must not contain duplicates")
        return value


class UpdateProgressRequest(BaseModel):
    user_id: int = 1
    completed_tasks: List[Dict[str, Any]] = Field(min_length=1, max_length=100)


@router.post("/generate")
async def generate_plan(
    request: GeneratePlanRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(request.user_id, current_user)

    # 确定要纳入计划的科目列表
    subject_ids = request.subjects
    if request.enrollment_id is not None:
        # 从报考记录中自动获取剩余未过科目
        enrollment_svc = EnrollmentService(db)
        remaining = enrollment_svc.get_remaining_subjects(current_user.id, request.enrollment_id)
        if not remaining:
            raise HTTPException(status_code=400, detail="该报考记录下所有科目已通过，无需生成学习计划。")
        subject_ids = remaining

    if not subject_ids:
        raise HTTPException(status_code=422, detail="请选择至少一门报考科目，或通过 enrollment_id 自动获取。")

    available_subject_ids = {
        subject_id
        for (subject_id,) in db.query(Subject.id).filter(Subject.id.in_(subject_ids)).all()
    }
    missing_subject_ids = sorted(set(subject_ids) - available_subject_ids)
    if missing_subject_ids:
        raise HTTPException(status_code=422, detail=f"Unknown subject ids: {missing_subject_ids}")
    service = PlannerService(db)
    return {
        "code": 0,
        "data": service.generate_study_plan(
            user_id=current_user.id,
            exam_date=request.exam_date,
            subjects=subject_ids,
            daily_hours=request.daily_hours,
            preferences=request.preferences,
            user_context=request.user_context,
        ),
    }


class AIAdviceRequest(BaseModel):
    user_context: str = Field(min_length=1, max_length=2000, description="用户个人情况描述")
    exam_date: Optional[datetime] = None
    subjects: Optional[List[int]] = None
    daily_hours: Optional[float] = Field(default=None, ge=0.5, le=12)


@router.post("/ai-advice")
async def get_ai_advice(
    request: AIAdviceRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get AI-generated study advice based on user's personal context."""
    service = PlannerService(db)
    subject_names = []
    if request.subjects:
        rows = db.query(Subject).filter(Subject.id.in_(request.subjects)).all()
        subject_names = [s.name for s in rows]
    weak_points = []
    for sid in (request.subjects or []):
        weak_points.extend(service.identify_weak_points(current_user.id, sid))

    advice = service.generate_ai_advice(
        user_context=request.user_context,
        exam_date=request.exam_date,
        subject_names=subject_names,
        daily_hours=request.daily_hours,
        weak_points=weak_points[:10],
    )
    return {"code": 0, "data": advice}


@router.get("/latest/{user_id}")
async def get_latest_plan(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    return {"code": 0, "data": PlannerService(db).get_latest_plan(user_id)}


@router.get("/plans/{user_id}")
async def get_plan_history(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    return {"code": 0, "data": PlannerService(db).get_plan_history(user_id, page, page_size)}


@router.post("/plans/{user_id}/{plan_id}/activate")
async def activate_plan(
    user_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    try:
        return {"code": 0, "data": PlannerService(db).activate_plan(user_id, plan_id)}
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.delete("/plans/{user_id}/{plan_id}")
async def delete_archived_plan(
    user_id: int,
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    try:
        PlannerService(db).delete_archived_plan(user_id, plan_id)
        return {"code": 0, "data": {"success": True}}
    except ValueError as exc:
        status_code = 409 if "active" in str(exc).lower() else 404
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/daily-tasks/{user_id}")
async def get_daily_tasks(
    user_id: int,
    date: Optional[datetime] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    return {"code": 0, "data": PlannerService(db).get_daily_tasks(user_id, date or datetime.now())}


@router.get("/weak-points/{user_id}/{subject_id}")
async def get_weak_points(
    user_id: int,
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    return {"code": 0, "data": PlannerService(db).identify_weak_points(user_id, subject_id)}


@router.post("/progress")
async def update_progress(
    request: UpdateProgressRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(request.user_id, current_user)
    return {"code": 0, "data": PlannerService(db).update_progress(request.user_id, request.completed_tasks)}


@router.get("/allocation")
async def allocate_time(
    total_days: int = Query(default=30, ge=1),
    daily_hours: float = Query(default=2, ge=0.5),
    user_id: int = Query(default=1, ge=1),
    subject_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
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
