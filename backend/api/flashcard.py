# -*- coding: utf-8 -*-
"""Flashcard API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.dependencies import get_current_user
from backend.models.user import User
from backend.services.flashcard_service import FlashcardService

router = APIRouter(prefix="/flashcards", tags=["flashcards"])


class GenerateCardsRequest(BaseModel):
    subject_id: int


class ReviewCardRequest(BaseModel):
    quality: int = Field(..., ge=0, le=5, description="0=完全忘记, 3=困难回忆, 5=轻松记住")


class CreateCardRequest(BaseModel):
    subject_id: int
    front: str = Field(..., min_length=1, max_length=2000)
    back: str = Field(..., min_length=1, max_length=5000)
    tags: Optional[str] = None


class SuspendCardRequest(BaseModel):
    suspend: bool = True


@router.post("/generate")
def generate_cards(
    request: GenerateCardsRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """为指定科目自动生成闪卡"""
    service = FlashcardService(db)
    result = service.generate_cards_for_subject(current_user.id, request.subject_id)
    return {"code": 0, "data": result}


@router.get("/due")
def get_due_cards(
    subject_id: Optional[int] = None,
    limit: int = Query(default=20, ge=1, le=50),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取今日到期需要复习的卡片"""
    service = FlashcardService(db)
    result = service.get_due_cards(current_user.id, subject_id, limit)
    return {"code": 0, "data": result}


@router.post("/{card_id}/review")
def review_card(
    card_id: int,
    request: ReviewCardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交卡片复习结果（SM-2评分）"""
    service = FlashcardService(db)
    try:
        result = service.review_card(card_id, current_user.id, request.quality)
        return {"code": 0, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/stats")
def get_stats(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取闪卡统计数据"""
    service = FlashcardService(db)
    result = service.get_stats(current_user.id, subject_id)
    return {"code": 0, "data": result}


@router.post("/custom")
def create_custom_card(
    request: CreateCardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """手动创建自定义闪卡"""
    service = FlashcardService(db)
    result = service.create_custom_card(
        user_id=current_user.id,
        subject_id=request.subject_id,
        front=request.front,
        back=request.back,
        tags=request.tags,
    )
    return {"code": 0, "data": result}


@router.patch("/{card_id}/suspend")
def suspend_card(
    card_id: int,
    request: SuspendCardRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """暂停或恢复卡片"""
    service = FlashcardService(db)
    success = service.suspend_card(card_id, current_user.id, request.suspend)
    if not success:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"code": 0, "data": {"success": True}}


@router.delete("/{card_id}")
def delete_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除闪卡"""
    service = FlashcardService(db)
    success = service.delete_card(card_id, current_user.id)
    if not success:
        raise HTTPException(status_code=404, detail="卡片不存在")
    return {"code": 0, "data": {"success": True}}
