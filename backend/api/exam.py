# -*- coding: utf-8 -*-
"""Exam API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.redis_client import redis_client
from backend.services.exam_engine import ExamEngine

router = APIRouter(prefix="/exam", tags=["exam"])


class GeneratePaperRequest(BaseModel):
    subject_id: int
    mode: str = "random"
    config: Optional[Dict[str, Any]] = None


class StartExamRequest(BaseModel):
    exam_id: int
    user_id: int = 1


class SubmitAnswerRequest(BaseModel):
    session_id: str
    question_id: int
    answer: str


class UpdateWrongQuestionRequest(BaseModel):
    is_mastered: Optional[bool] = None
    tags: Optional[List[str]] = None
    note: Optional[str] = None


def _split_ints(value: Optional[str]) -> Optional[List[int]]:
    if not value:
        return None
    return [int(item) for item in value.split(",") if item.strip()]


@router.post("/generate")
async def generate_paper(request: GeneratePaperRequest, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    return {"code": 0, "data": engine.generate_paper(request.subject_id, request.mode, request.config)}


@router.post("/start")
async def start_exam(request: StartExamRequest, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.start_exam(request.exam_id, request.user_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submit-answer")
async def submit_answer(request: SubmitAnswerRequest, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    return {"code": 0, "data": engine.submit_answer(request.session_id, request.question_id, request.answer)}


@router.post("/submit/{session_id}")
async def submit_paper(session_id: str, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.submit_paper(session_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/history/{user_id}")
async def get_exam_history(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    engine = ExamEngine(db, redis_client)
    return {"code": 0, "data": engine.get_exam_history(user_id, page, page_size)}


@router.get("/session/{session_id}")
async def get_session_detail(session_id: str, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.get_session_detail(session_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/wrong-questions/{user_id}/export")
async def export_wrong_questions(
    user_id: int,
    subject_id: Optional[int] = None,
    chapter_ids: Optional[str] = None,
    is_mastered: Optional[bool] = None,
    keyword: Optional[str] = None,
    format: str = Query(default="markdown", pattern="^(markdown|md|csv|word|doc)$"),
    db: Session = Depends(get_db),
):
    engine = ExamEngine(db, redis_client)
    payload = engine.export_wrong_questions(
        user_id=user_id,
        export_format="markdown" if format == "md" else format,
        subject_id=subject_id,
        chapter_ids=_split_ints(chapter_ids),
        is_mastered=is_mastered,
        keyword=keyword,
    )
    return Response(
        content=payload["content"],
        media_type=payload["media_type"],
        headers={"Content-Disposition": f'attachment; filename="{payload["filename"]}"'},
    )


@router.get("/wrong-questions/{user_id}")
async def get_wrong_questions(
    user_id: int,
    subject_id: Optional[int] = None,
    chapter_ids: Optional[str] = None,
    is_mastered: Optional[bool] = None,
    keyword: Optional[str] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    engine = ExamEngine(db, redis_client)
    return {
        "code": 0,
        "data": engine.get_wrong_questions(
            user_id=user_id,
            subject_id=subject_id,
            chapter_ids=_split_ints(chapter_ids),
            is_mastered=is_mastered,
            keyword=keyword,
            page=page,
            page_size=page_size,
        ),
    }


@router.patch("/wrong-questions/{user_id}/{question_id}")
async def update_wrong_question(
    user_id: int,
    question_id: int,
    request: UpdateWrongQuestionRequest,
    db: Session = Depends(get_db),
):
    engine = ExamEngine(db, redis_client)
    result = engine.update_wrong_question(
        user_id=user_id,
        question_id=question_id,
        is_mastered=request.is_mastered,
        tags=request.tags,
        note=request.note,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Wrong question not found.")
    return {"code": 0, "data": result}


@router.delete("/wrong-questions/{user_id}/{question_id}")
async def remove_wrong_question(user_id: int, question_id: int, db: Session = Depends(get_db)):
    engine = ExamEngine(db, redis_client)
    success = engine.remove_wrong_question(user_id, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wrong question not found.")
    return {"code": 0, "data": {"success": True}}
