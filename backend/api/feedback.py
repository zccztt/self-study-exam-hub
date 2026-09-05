# -*- coding: utf-8 -*-
"""AI 评分纠正反馈 API"""

from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db
from backend.models.user import User

router = APIRouter(prefix="/feedback", tags=["feedback"])


class FeedbackCreate(BaseModel):
    session_id: str
    question_id: int
    feedback_type: Literal["score_error", "explanation_error", "missing_point", "other"]
    expected_score: Optional[int] = Field(default=None, ge=0, le=100)
    reason: str = Field(..., min_length=1, max_length=2000)
    evidence: Optional[str] = None  # 用户提供的依据（教材引用等）


class FeedbackResponse(BaseModel):
    id: int
    status: str
    created_at: str


@router.post("", response_model=FeedbackResponse)
def submit_feedback(
    body: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """提交 AI 评分纠正反馈"""
    from backend.models.feedback import GradingFeedback

    feedback = GradingFeedback(
        user_id=current_user.id,
        session_id=body.session_id,
        question_id=body.question_id,
        feedback_type=body.feedback_type,
        expected_score=body.expected_score,
        reason=body.reason,
        evidence=body.evidence,
        status="pending",
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return FeedbackResponse(
        id=feedback.id,
        status=feedback.status,
        created_at=feedback.created_at.isoformat() if feedback.created_at else "",
    )


@router.get("")
def list_my_feedback(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看我提交的反馈列表（分页）"""
    from backend.models.feedback import GradingFeedback

    base_query = db.query(GradingFeedback).filter(GradingFeedback.user_id == current_user.id)
    total = base_query.count()
    items = (
        base_query
        .order_by(GradingFeedback.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": [
            {
                "id": f.id,
                "session_id": f.session_id,
                "question_id": f.question_id,
                "feedback_type": f.feedback_type,
                "status": f.status,
                "reason": f.reason,
                "created_at": f.created_at.isoformat() if f.created_at else "",
            }
            for f in items
        ],
    }
