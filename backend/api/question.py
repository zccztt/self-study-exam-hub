# -*- coding: utf-8 -*-
"""Question bank API routes."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.elasticsearch_client import es_client
from backend.services.question_service import QuestionService

router = APIRouter(prefix="/questions", tags=["questions"])


class AddToFavoritesRequest(BaseModel):
    user_id: int = 1
    question_id: int
    tags: Optional[List[str]] = None


def _split_ints(value: Optional[str]) -> Optional[List[int]]:
    if not value:
        return None
    return [int(item) for item in value.split(",") if item.strip()]


def _split_strings(value: Optional[str]) -> Optional[List[str]]:
    if not value:
        return None
    return [item.strip() for item in value.split(",") if item.strip()]


@router.get("/search")
async def search_questions(
    keyword: Optional[str] = None,
    subject_id: Optional[int] = None,
    years: Optional[str] = None,
    question_types: Optional[str] = None,
    difficulty: Optional[str] = None,
    chapter_ids: Optional[str] = None,
    high_frequency: Optional[bool] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = QuestionService(db, es_client)
    result = service.search_questions(
        keyword=keyword,
        subject_id=subject_id,
        years=_split_ints(years),
        question_types=_split_strings(question_types),
        difficulty=difficulty,
        chapter_ids=_split_ints(chapter_ids),
        high_frequency=high_frequency,
        page=page,
        page_size=page_size,
    )
    return {"code": 0, "data": result}


@router.get("/high-frequency/{subject_id}")
async def get_high_frequency_questions(
    subject_id: int,
    limit: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = QuestionService(db, es_client)
    return {"code": 0, "data": service.get_high_frequency_questions(subject_id, limit)}


@router.post("/favorites")
async def add_to_favorites(request: AddToFavoritesRequest, db: Session = Depends(get_db)):
    service = QuestionService(db, es_client)
    success = service.add_to_favorites(request.user_id, request.question_id, request.tags)
    if not success:
        raise HTTPException(status_code=404, detail="Question not found.")
    return {"code": 0, "data": {"success": True}}


@router.get("/favorites/{user_id}")
async def get_favorites(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    service = QuestionService(db, es_client)
    return {"code": 0, "data": service.get_favorites(user_id, page, page_size)}


@router.delete("/favorites/{user_id}/{question_id}")
async def remove_from_favorites(user_id: int, question_id: int, db: Session = Depends(get_db)):
    service = QuestionService(db, es_client)
    success = service.remove_from_favorites(user_id, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Favorite not found.")
    return {"code": 0, "data": {"success": True}}


@router.get("/{question_id}")
async def get_question_detail(question_id: int, db: Session = Depends(get_db)):
    service = QuestionService(db, es_client)
    result = service.get_question_detail(question_id)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found.")
    return {"code": 0, "data": result}
