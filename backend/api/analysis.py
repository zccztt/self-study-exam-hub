# -*- coding: utf-8 -*-
"""Analysis API routes."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.services.analysis_service import AnalysisService

router = APIRouter(prefix="/analysis", tags=["analysis"])


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
