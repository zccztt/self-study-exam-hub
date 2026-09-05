# -*- coding: utf-8 -*-
"""Analysis API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.api.dependencies import get_current_user, require_self
from backend.models.user import User
from backend.services.analysis_service import AnalysisService
from backend.config import settings
from backend.utils.rate_limit import rate_limiter
from backend.services.ai_provider_pool import ai_provider_pool

router = APIRouter(prefix="/analysis", tags=["analysis"])


@router.get("/ai-providers/status")
async def get_ai_provider_status(current_user: User = Depends(get_current_user)):
    """Return non-secret provider pool and health information."""
    return {"code": 0, "data": ai_provider_pool.public_status()}


@router.get("/knowledge-tree/{subject_id}")
async def get_knowledge_tree(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).get_knowledge_tree(subject_id)}


@router.get("/high-frequency/{subject_id}")
async def get_high_frequency_points(
    subject_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return {"code": 0, "data": AnalysisService(db).get_high_frequency_points(subject_id, limit)}


@router.get("/trend/{subject_id}/{point_id}")
async def get_point_trend(
    subject_id: int,
    point_id: int,
    years: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(get_db),
):
    return {"code": 0, "data": AnalysisService(db).get_point_trend(subject_id, point_id, years)}


@router.get("/word-cloud/{subject_id}")
async def get_word_cloud(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).get_word_cloud_data(subject_id)}


@router.get("/knowledge-network/{subject_id}")
async def get_knowledge_network(
    subject_id: int,
    limit: int = Query(default=30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return {"code": 0, "data": AnalysisService(db).get_knowledge_network(subject_id, limit)}


@router.get("/chapter-heatmap/{subject_id}")
async def get_chapter_heatmap(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).get_chapter_heatmap(subject_id)}


@router.get("/question-types/{subject_id}")
async def get_question_type_distribution(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).get_question_type_distribution(subject_id)}


@router.get("/prediction/{subject_id}")
async def predict_next_exam(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).predict_next_exam(subject_id)}


@router.get("/hotspots/{subject_id}")
async def get_hotspot_alerts(subject_id: int, db: Session = Depends(get_db)):
    return {"code": 0, "data": AnalysisService(db).get_hotspot_alerts(subject_id)}


@router.get("/score-trends/{user_id}")
async def get_score_trends(
    user_id: int,
    subject_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_self(user_id, current_user)
    return {"code": 0, "data": AnalysisService(db).get_score_trends(user_id, subject_id, limit)}


@router.get("/ai-hotspots/{subject_id}")
def ai_analyze_hotspots(
    subject_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """AI 智能分析高频考点，生成备考建议和考点预测。

    从本地配置文件读取 AI API 配置，未配置时回退到纯统计分析。
    """
    rate_limiter.check("ai_analysis", f"user:{current_user.id}", settings.AI_RATE_LIMIT_PER_MINUTE)
    return {"code": 0, "data": AnalysisService(db).ai_analyze_hotspots(subject_id)}


@router.get("/templates")
async def get_answer_templates():
    """获取所有答题模板"""
    from backend.services.answer_template_service import AnswerTemplateService
    service = AnswerTemplateService()
    return {"code": 0, "data": service.get_all_templates()}


@router.get("/templates/{question_type}")
async def get_template_by_type(
    question_type: str,
    category: str = Query(default="default"),
):
    """获取某题型的答题模板"""
    from backend.services.answer_template_service import AnswerTemplateService
    service = AnswerTemplateService()
    template = service.get_template(question_type, category)
    if not template:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="模板不存在")
    return {"code": 0, "data": template}


@router.get("/sprint-report/{user_id}/{subject_id}")
async def get_sprint_report(
    user_id: int,
    subject_id: int,
    exam_date: str | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """生成考前冲刺报告"""
    require_self(user_id, current_user)
    from datetime import datetime
    from backend.services.sprint_report_service import SprintReportService
    service = SprintReportService(db)
    exam_dt = datetime.fromisoformat(exam_date) if exam_date else None
    return {"code": 0, "data": service.generate_report(user_id, subject_id, exam_dt)}
