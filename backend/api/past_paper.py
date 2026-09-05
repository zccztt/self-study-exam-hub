# -*- coding: utf-8 -*-
"""Past paper (历年真题) API routes."""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_optional_current_user
from backend.database import get_db
from backend.models.user import User
from backend.services.past_paper_service import PastPaperService

router = APIRouter(prefix="/past-papers", tags=["past-papers"])


@router.get("")
def list_past_papers(
    subject_id: Optional[int] = None,
    year: Optional[int] = None,
    month: Optional[int] = None,
    province_id: Optional[int] = None,
    paper_type: Optional[str] = Query(default=None, description="筛选类型: real=真题, mock=模拟题, 不传=全部"),
    keyword: Optional[str] = Query(default=None, description="按课程代码或课程名称搜索"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """获取历年真题列表（支持筛选和分页）"""
    service = PastPaperService(db)
    return {
        "code": 0,
        "data": service.list_papers(
            subject_id=subject_id,
            year=year,
            month=month,
            province_id=province_id,
            paper_type=paper_type,
            keyword=keyword,
            page=page,
            page_size=page_size,
        ),
    }


@router.get("/subjects")
def get_available_subjects(
    paper_type: Optional[str] = Query(default=None, description="筛选类型: real/mock"),
    db: Session = Depends(get_db),
):
    """获取拥有真题的科目列表"""
    service = PastPaperService(db)
    return {"code": 0, "data": service.get_available_subjects(paper_type=paper_type)}


@router.get("/years")
def get_available_years(
    subject_id: Optional[int] = None,
    paper_type: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """获取可选考试年份"""
    service = PastPaperService(db)
    return {"code": 0, "data": service.get_available_years(subject_id=subject_id, paper_type=paper_type)}


@router.get("/{paper_id}")
def get_paper_detail(
    paper_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取真题试卷详情（含题目，不含答案，需登录）"""
    service = PastPaperService(db)
    detail = service.get_paper_detail(paper_id)
    if not detail:
        raise HTTPException(status_code=404, detail="真题试卷不存在")
    return {"code": 0, "data": detail}


class StartPaperRequest(BaseModel):
    user_id: Optional[int] = None


@router.post("/{paper_id}/start")
def start_past_paper(
    paper_id: int,
    body: StartPaperRequest = StartPaperRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """开始做真题（创建考试会话）"""
    service = PastPaperService(db)
    try:
        result = service.start_paper(paper_id, current_user.id)
        return {"code": 0, "data": result}
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
