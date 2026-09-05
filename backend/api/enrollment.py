# -*- coding: utf-8 -*-
"""Enrollment API routes: provinces, schools, majors, user enrollment & subject status."""

from datetime import date
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, require_self
from backend.database import get_db
from backend.models.user import User
from backend.services.enrollment_service import EnrollmentService

router = APIRouter(prefix="/enrollment", tags=["enrollment"])


# ------------------------------------------------------------------
# Pydantic schemas
# ------------------------------------------------------------------

class EnrollmentCreate(BaseModel):
    major_id: int
    target_date: Optional[str] = None  # 接受任意格式日期字符串，如 "2027-06", "2027-06-01"


class EnrollmentUpdate(BaseModel):
    target_date: Optional[str] = None


class SubjectStatusUpdate(BaseModel):
    enrollment_id: int
    subject_id: int
    status: Literal["not_taken", "passed", "failed"] = Field(..., description="not_taken / passed / failed")
    score: Optional[float] = Field(default=None, ge=0, le=100)
    exam_date: Optional[date] = None
    certificate_no: Optional[str] = None
    note: Optional[str] = None


# ------------------------------------------------------------------
# Public: Province / School / Major lookup
# ------------------------------------------------------------------

@router.get("/provinces")
async def list_provinces(db: Session = Depends(get_db)):
    svc = EnrollmentService(db)
    return {"code": 0, "data": svc.list_provinces()}


@router.get("/schools")
async def list_schools(
    province_id: Optional[int] = Query(default=None),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    return {"code": 0, "data": svc.list_schools(province_id=province_id)}


@router.get("/majors")
async def list_majors(
    province_id: Optional[int] = Query(default=None),
    school_id: Optional[int] = Query(default=None),
    level: Optional[str] = Query(default=None, description="zk / bk"),
    q: Optional[str] = Query(default=None, description="搜索专业名或代码"),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    return {"code": 0, "data": svc.list_majors(province_id=province_id, school_id=school_id, level=level, q=q)}


@router.get("/majors/{major_id}/subjects")
async def get_major_subjects(major_id: int, db: Session = Depends(get_db)):
    """查看专业考试计划（无需登录）"""
    svc = EnrollmentService(db)
    data = svc.get_major_subjects(major_id)
    if not data:
        raise HTTPException(status_code=404, detail="专业不存在或暂无考试计划")
    return {"code": 0, "data": data}


@router.get("/replacement-map")
async def get_replacement_map(db: Session = Depends(get_db)):
    """获取全部新旧课程替代对照数据（无需登录）"""
    from backend.services.enrollment_service import _REPLACEMENT_INFO
    from backend.models.subject import Subject

    # 批量查新课程名称
    new_codes = list(_REPLACEMENT_INFO.keys())
    subjects = (
        db.query(Subject.code, Subject.name)
        .filter(Subject.code.in_(new_codes))
        .all()
    ) if new_codes else []
    name_map = {s.code: s.name for s in subjects}

    items = []
    for new_code, info in sorted(_REPLACEMENT_INFO.items()):
        items.append({
            "new_code": new_code,
            "new_name": name_map.get(new_code, new_code),
            "old_code": info["old_code"],
            "old_name": info["old_name"],
            "note": info["note"],
        })
    return {"code": 0, "data": items}


# ------------------------------------------------------------------
# User enrollment CRUD
# ------------------------------------------------------------------

@router.post("")
async def create_enrollment(
    body: EnrollmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    # 解析 target_date：支持 "2027-06", "2027-06-01", "" 或 None
    parsed_date = None
    if body.target_date:
        raw = body.target_date.strip()
        if raw:
            try:
                from datetime import datetime as dt
                if len(raw) <= 7:  # "2027-06" 格式
                    parsed_date = dt.strptime(raw, "%Y-%m").date()
                else:
                    parsed_date = dt.strptime(raw[:10], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=422, detail="日期格式无效，请使用 YYYY-MM 或 YYYY-MM-DD")
    try:
        result = svc.create_enrollment(
            user_id=current_user.id,
            major_id=body.major_id,
            target_date=parsed_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": result}


@router.get("/list")
async def list_user_enrollments(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    return {"code": 0, "data": svc.list_enrollments(current_user.id)}


@router.delete("/{enrollment_id}")
async def delete_enrollment(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    try:
        svc.delete_enrollment(current_user.id, enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "message": "已取消报考"}


@router.put("/{enrollment_id}")
async def update_enrollment(
    enrollment_id: int,
    body: EnrollmentUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    svc = EnrollmentService(db)
    parsed_date = None
    if body.target_date:
        raw = body.target_date.strip()
        if raw:
            try:
                from datetime import datetime as dt
                if len(raw) <= 7:
                    parsed_date = dt.strptime(raw, "%Y-%m").date()
                else:
                    parsed_date = dt.strptime(raw[:10], "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=422, detail="日期格式无效")
    try:
        result = svc.update_enrollment(
            user_id=current_user.id,
            enrollment_id=enrollment_id,
            target_date=parsed_date,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": result}


# ------------------------------------------------------------------
# Enrollment subjects & status
# ------------------------------------------------------------------

@router.get("/{enrollment_id}/subjects")
async def get_enrollment_subjects(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取报考专业的全部考试科目及状态"""
    svc = EnrollmentService(db)
    try:
        data = svc.get_enrollment_subjects(current_user.id, enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    # 确保每个科目都带替代字段（即使为 None），避免被 JSON 序列化丢弃
    for group in data.get("subjects", {}).values():
        if not isinstance(group, list):
            continue
        for item in group:
            item.setdefault("replaced_from_code", None)
            item.setdefault("replaced_from_name", None)
            item.setdefault("replacement_note", None)
    return {"code": 0, "data": data}


@router.put("/subject-status")
async def update_subject_status(
    body: SubjectStatusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """更新科目考试状态（标记已过/未过/重置）"""
    svc = EnrollmentService(db)
    try:
        result = svc.update_subject_status(
            user_id=current_user.id,
            enrollment_id=body.enrollment_id,
            subject_id=body.subject_id,
            status=body.status,
            score=body.score,
            exam_date=body.exam_date,
            certificate_no=body.certificate_no,
            note=body.note,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": result}


@router.get("/{enrollment_id}/progress")
async def get_enrollment_progress(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取毕业进度统计"""
    svc = EnrollmentService(db)
    try:
        data = svc.get_progress(current_user.id, enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return {"code": 0, "data": data}


@router.get("/{enrollment_id}/remaining-subjects")
async def get_remaining_subjects(
    enrollment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取剩余未通过科目 ID 列表（供学习计划使用）"""
    svc = EnrollmentService(db)
    return {"code": 0, "data": svc.get_remaining_subjects(current_user.id, enrollment_id)}


@router.get("/recommendation")
async def get_course_recommendation(
    enrollment_id: Optional[int] = Query(default=None, description="指定报考ID，不传则综合全部报考"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """获取个性化报考课程建议和学习计划"""
    from backend.services.recommendation_service import CourseRecommendationService
    svc = CourseRecommendationService(db)
    try:
        data = svc.get_recommendation(current_user.id, enrollment_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"code": 0, "data": data}
