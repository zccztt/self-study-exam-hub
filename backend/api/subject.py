# -*- coding: utf-8 -*-
"""Subject API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.dependencies import get_optional_current_user
from backend.config import settings
from backend.data.self_exam_catalog import normalize_course_code
from backend.models.chapter import Chapter
from backend.models.exam import Exam
from backend.models.question import Question
from backend.models.subject import Subject
from backend.models.video import Video
from backend.services.online_question_provider import TEMP_ONLINE_SOURCE_PREFIX
from backend.services.learning_resource_service import LearningResourceService
from backend.utils.rate_limit import rate_limiter

router = APIRouter(prefix="/subjects", tags=["subjects"])


def _searchable_question_filter():
    return or_(Question.source.is_(None), ~Question.source.like(f"{TEMP_ONLINE_SOURCE_PREFIX}%"))


@router.get("")
async def get_subjects(
    q: Optional[str] = Query(default=None, description="课程代码或课程名称"),
    has_content: Optional[bool] = Query(default=None, description="只返回有题目或视频的课程"),
    db: Session = Depends(get_db),
):
    question_counts = (
        db.query(Question.subject_id.label("subject_id"), func.count(Question.id).label("question_count"))
        .filter(_searchable_question_filter())
        .group_by(Question.subject_id)
        .subquery()
    )
    video_counts = (
        db.query(Video.subject_id.label("subject_id"), func.count(Video.id).label("video_count"))
        .filter(Video.is_active.is_(True))
        .group_by(Video.subject_id)
        .subquery()
    )
    question_count = func.coalesce(question_counts.c.question_count, 0)
    video_count = func.coalesce(video_counts.c.video_count, 0)
    query = (
        db.query(Subject, question_count.label("question_count"), video_count.label("video_count"))
        .outerjoin(question_counts, Subject.id == question_counts.c.subject_id)
        .outerjoin(video_counts, Subject.id == video_counts.c.subject_id)
    )
    if q:
        keyword = q.strip()
        normalized_code = normalize_course_code(keyword)
        pattern = f"%{keyword}%"
        query = query.filter((Subject.code == normalized_code) | Subject.name.ilike(pattern))
    if has_content is True:
        query = query.filter(or_(question_count > 0, video_count > 0))

    rows = query.order_by((question_count + video_count).desc(), Subject.code.asc(), Subject.id.asc()).all()
    return {
        "code": 0,
        "data": [
            {
                "id": subject.id,
                "name": subject.name,
                "code": subject.code,
                "category": subject.category,
                "exam_duration": subject.exam_duration,
                "total_score": subject.total_score,
                "description": subject.description,
                "question_count": int(subject_question_count or 0),
                "video_count": int(subject_video_count or 0),
                "has_content": bool(subject_question_count or subject_video_count),
            }
            for subject, subject_question_count, subject_video_count in rows
        ],
    }


@router.get("/overview")
async def get_content_overview(db: Session = Depends(get_db)):
    searchable_questions = db.query(Question).filter(_searchable_question_filter())
    return {
        "code": 0,
        "data": {
            "subject_count": db.query(func.count(Subject.id)).scalar() or 0,
            "subjects_with_questions": searchable_questions.with_entities(
                func.count(func.distinct(Question.subject_id))
            ).scalar() or 0,
            "question_count": searchable_questions.with_entities(func.count(Question.id)).scalar() or 0,
            "exam_count": db.query(func.count(Exam.id)).scalar() or 0,
            "video_count": db.query(func.count(Video.id)).filter(Video.is_active.is_(True)).scalar() or 0,
        },
    }


@router.get("/{subject_id}/learning-resources")
def get_learning_resources(
    subject_id: int,
    online_search: bool = Query(default=False),
    limit: int = Query(default=10, ge=1, le=30),
    db: Session = Depends(get_db),
    current_user=Depends(get_optional_current_user),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")
    if online_search and not current_user:
        raise HTTPException(status_code=401, detail="登录后才能联网筛查学习资源。")
    if online_search:
        rate_limiter.check(
            "online_learning_resource_search",
            f"user:{current_user.id}",
            settings.EXTERNAL_SEARCH_RATE_LIMIT_PER_MINUTE,
        )
    return {
        "code": 0,
        "data": LearningResourceService().list_resources(subject, online_search=online_search, limit=limit),
    }


@router.get("/{subject_id}")
async def get_subject_detail(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found.")

    chapters = (
        db.query(Chapter)
        .filter(Chapter.subject_id == subject_id)
        .order_by(Chapter.order.asc(), Chapter.id.asc())
        .all()
    )
    question_count = (
        db.query(func.count(Question.id))
        .filter(Question.subject_id == subject_id, _searchable_question_filter())
        .scalar()
        or 0
    )
    video_count = (
        db.query(func.count(Video.id))
        .filter(Video.subject_id == subject_id, Video.is_active.is_(True))
        .scalar()
        or 0
    )
    return {
        "code": 0,
        "data": {
            "id": subject.id,
            "name": subject.name,
            "code": subject.code,
            "category": subject.category,
            "description": subject.description,
            "exam_duration": subject.exam_duration,
            "total_score": subject.total_score,
            "question_count": question_count,
            "video_count": video_count,
            "has_content": bool(question_count or video_count),
            "chapters": [
                {
                    "id": chapter.id,
                    "name": chapter.name,
                    "order": chapter.order,
                    "description": chapter.description,
                }
                for chapter in chapters
            ],
        },
    }
