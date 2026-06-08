# -*- coding: utf-8 -*-
"""Subject API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.data.self_exam_catalog import normalize_course_code
from backend.models.chapter import Chapter
from backend.models.subject import Subject

router = APIRouter(prefix="/subjects", tags=["subjects"])


@router.get("")
async def get_subjects(
    q: Optional[str] = Query(default=None, description="课程代码或课程名称"),
    db: Session = Depends(get_db),
):
    query = db.query(Subject)
    if q:
        keyword = q.strip()
        normalized_code = normalize_course_code(keyword)
        pattern = f"%{keyword}%"
        query = query.filter((Subject.code == normalized_code) | Subject.name.ilike(pattern))

    subjects = query.order_by(Subject.code.asc(), Subject.id.asc()).all()
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
            }
            for subject in subjects
        ],
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
            "chapters": [
                {"id": chapter.id, "name": chapter.name, "order": chapter.order}
                for chapter in chapters
            ],
        },
    }
