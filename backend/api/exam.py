# -*- coding: utf-8 -*-
"""Exam API routes."""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.dependencies import get_current_user, require_self
from backend.models.exam import ExamSession, ExamResult
from backend.models.user import User
from backend.models.planner import UserMastery
from backend.models.chapter import KnowledgePoint, Chapter, QuestionKnowledgePoint
from backend.models.question import Question
from backend.redis_client import redis_client
from backend.services.exam_engine import ExamEngine
from backend.config import settings
from backend.utils.rate_limit import rate_limiter

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
    try:
        return [int(item) for item in value.split(",") if item.strip()]
    except (ValueError, TypeError):
        return None


@router.post("/generate")
def generate_paper(
    request: GeneratePaperRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    config = dict(request.config or {})
    config["user_id"] = current_user.id
    if config.get("online_fallback"):
        rate_limiter.check(
            "online_exam_generation",
            f"user:{current_user.id}",
            settings.EXTERNAL_SEARCH_RATE_LIMIT_PER_MINUTE,
        )
    engine = ExamEngine(db, redis_client)
    return {"code": 0, "data": engine.generate_paper(request.subject_id, request.mode, config)}


@router.post("/start")
async def start_exam(
    request: StartExamRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(request.user_id, current_user)
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.start_exam(request.exam_id, current_user.id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/submit-answer")
async def submit_answer(
    request: SubmitAnswerRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_session_owner(db, request.session_id, current_user.id)
    engine = ExamEngine(db, redis_client)
    result = engine.submit_answer(request.session_id, request.question_id, request.answer)
    if not result.get("success"):
        raise HTTPException(status_code=409, detail=result.get("message") or "答案保存失败。")
    return {"code": 0, "data": result}


@router.post("/submit/{session_id}")
def submit_paper(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_session_owner(db, session_id, current_user.id)
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.submit_paper(session_id)}
    except ValueError as exc:
        status_code = 404 if "not found" in str(exc).lower() else 409
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc


@router.get("/history/{user_id}")
async def get_exam_history(
    user_id: int,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    engine = ExamEngine(db, redis_client)
    return {"code": 0, "data": engine.get_exam_history(user_id, page, page_size)}


@router.get("/session/{session_id}")
async def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_session_owner(db, session_id, current_user.id)
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.get_session_detail(session_id)}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/session/{session_id}")
async def cancel_exam(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _require_session_owner(db, session_id, current_user.id)
    engine = ExamEngine(db, redis_client)
    try:
        return {"code": 0, "data": engine.cancel_exam(session_id)}
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/wrong-questions/{user_id}/export")
async def export_wrong_questions(
    user_id: int,
    subject_id: Optional[int] = None,
    chapter_ids: Optional[str] = None,
    is_mastered: Optional[bool] = None,
    keyword: Optional[str] = None,
    format: str = Query(default="markdown", pattern="^(markdown|md|csv|word|doc)$"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
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
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
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
async def remove_wrong_question(
    user_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    engine = ExamEngine(db, redis_client)
    success = engine.remove_wrong_question(user_id, question_id)
    if not success:
        raise HTTPException(status_code=404, detail="Wrong question not found.")
    return {"code": 0, "data": {"success": True}}


@router.get("/sessions/{session_id}/ai-grading")
async def get_ai_grading_for_review(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取 AI 评分结果供用户审核"""
    session = db.query(ExamSession).filter(
        ExamSession.session_id == session_id,
        ExamSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="考试会话不存在")
    result = db.query(ExamResult).filter(ExamResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="评分结果不存在")
    return {
        "session_id": session_id,
        "status": session.ai_grading_status,
        "result": result.result,
    }


class ConfirmAiGradingRequest(BaseModel):
    modifications: Optional[Dict[str, Dict[str, Any]]] = None


@router.post("/sessions/{session_id}/ai-grading/confirm")
async def confirm_ai_grading(
    session_id: str,
    body: ConfirmAiGradingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """确认或修改 AI 评分结果"""
    session = db.query(ExamSession).filter(
        ExamSession.session_id == session_id,
        ExamSession.user_id == current_user.id,
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="考试会话不存在")
    result = db.query(ExamResult).filter(ExamResult.session_id == session_id).first()
    if not result:
        raise HTTPException(status_code=404, detail="评分结果不存在")

    modifications = body.modifications or {}
    if modifications:
        # 用户修改了某些题目的分数
        current_result = result.result or {}
        for q_id, mod in modifications.items():
            if q_id in current_result.get("details", {}):
                detail = current_result["details"][q_id]
                if "score" in mod:
                    detail["score"] = mod["score"]
                if "comment" in mod:
                    detail["user_comment"] = mod["comment"]
                detail["user_modified"] = True
        # 重算总分
        total = sum(d.get("score", 0) for d in current_result.get("details", {}).values())
        current_result["total_score"] = total
        result.result = current_result
        session.ai_grading_status = "user_modified"
    else:
        session.ai_grading_status = "confirmed"

    db.commit()
    return {"status": "ok", "new_status": session.ai_grading_status}


@router.get("/weak-points/{user_id}")
async def get_weak_points_for_practice(
    user_id: int,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户薄弱知识点列表，供薄弱专练模式选择"""
    require_self(user_id, current_user)

    if subject_id:
        # 使用 PlannerService 的识别逻辑
        from backend.services.planner_service import PlannerService
        planner = PlannerService(db)
        points = planner.identify_weak_points(user_id, subject_id)
    else:
        # 跨科目汇总
        from backend.models.exam import WrongQuestion
        weak = (
            db.query(UserMastery, KnowledgePoint, Chapter)
            .join(KnowledgePoint, UserMastery.knowledge_point_id == KnowledgePoint.id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(
                UserMastery.user_id == user_id,
                UserMastery.mastery_level < 0.8,
            )
            .order_by(UserMastery.mastery_level.asc())
            .limit(20)
            .all()
        )
        points = [
            {
                "point_id": m.knowledge_point_id,
                "name": kp.name,
                "description": kp.description or "",
                "chapter_id": kp.chapter_id,
                "subject_id": ch.subject_id,
                "mastery_level": m.mastery_level,
                "correct_count": m.correct_count,
                "wrong_count": m.wrong_count,
                "priority": "high" if m.mastery_level < 0.6 else "medium",
            }
            for m, kp, ch in weak
        ]

        # 如果没有掌握度数据，从错题中推导
        if not points:
            from sqlalchemy import func as sa_func
            wrong_points = (
                db.query(
                    KnowledgePoint.id,
                    KnowledgePoint.name,
                    KnowledgePoint.description,
                    KnowledgePoint.chapter_id,
                    Chapter.subject_id,
                    sa_func.count(QuestionKnowledgePoint.question_id).label("wrong_count"),
                )
                .join(QuestionKnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
                .join(WrongQuestion, QuestionKnowledgePoint.question_id == WrongQuestion.question_id)
                .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
                .filter(
                    WrongQuestion.user_id == user_id,
                    WrongQuestion.is_mastered.is_(False),
                )
                .group_by(
                    KnowledgePoint.id,
                    KnowledgePoint.name,
                    KnowledgePoint.description,
                    KnowledgePoint.chapter_id,
                    Chapter.subject_id,
                )
                .order_by(sa_func.count(QuestionKnowledgePoint.question_id).desc())
                .limit(20)
                .all()
            )
            points = [
                {
                    "point_id": row[0],
                    "name": row[1],
                    "description": row[2] or "",
                    "chapter_id": row[3],
                    "subject_id": row[4],
                    "mastery_level": max(0.2, round(1 - min(row[5], 5) / 6, 2)),
                    "correct_count": 0,
                    "wrong_count": row[5],
                    "priority": "high",
                }
                for row in wrong_points
            ]

    return {"code": 0, "data": {"items": points, "total": len(points)}}


def _require_session_owner(db: Session, session_id: str, user_id: int) -> ExamSession:
    session = db.query(ExamSession).filter(ExamSession.session_id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="考试会话不存在。")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问该考试会话。")
    return session
