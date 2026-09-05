# -*- coding: utf-8 -*-
"""Admin API for crawl data management."""

import os
import re
import subprocess
import sys
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.models.crawl_log import CrawlLog
from backend.models.enrollment import Major, MajorSubject, Province, School
from backend.models.user import User

router = APIRouter(prefix="/admin/crawl", tags=["admin-crawl"])


def _require_admin(user: User):
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="需要管理员权限")


# ------------------------------------------------------------------
# Crawl logs
# ------------------------------------------------------------------

@router.get("/logs")
async def list_crawl_logs(
    province_code: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """查看爬取日志"""
    _require_admin(current_user)
    query = db.query(CrawlLog)
    if province_code:
        query = query.filter(CrawlLog.province_code == province_code)
    if source:
        query = query.filter(CrawlLog.source == source)

    total = query.count()
    logs = (
        query.order_by(desc(CrawlLog.created_at))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "code": 0,
        "data": {
            "total": total,
            "page": page,
            "items": [
                {
                    "id": log.id,
                    "source": log.source,
                    "province_code": log.province_code,
                    "status": log.status,
                    "schools_found": log.schools_found,
                    "majors_found": log.majors_found,
                    "majors_created": log.majors_created,
                    "majors_updated": log.majors_updated,
                    "courses_found": log.courses_found,
                    "links_created": log.links_created,
                    "error_count": log.error_count,
                    "errors": log.errors,
                    "duration_seconds": log.duration_seconds,
                    "started_at": log.started_at.isoformat() if log.started_at else None,
                    "finished_at": log.finished_at.isoformat() if log.finished_at else None,
                }
                for log in logs
            ],
        },
    }


# ------------------------------------------------------------------
# Data statistics
# ------------------------------------------------------------------

@router.get("/stats")
async def get_data_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取院校专业数据统计"""
    _require_admin(current_user)

    # Per-province stats
    provinces = db.query(Province).order_by(Province.code).all()
    province_stats = []
    for p in provinces:
        major_count = db.query(Major).filter(Major.province_id == p.id).count()
        school_count = db.query(School).filter(School.province_id == p.id).count()
        link_count = (
            db.query(MajorSubject)
            .join(Major, MajorSubject.major_id == Major.id)
            .filter(Major.province_id == p.id)
            .count()
        )
        # Last crawl
        last_crawl = (
            db.query(CrawlLog)
            .filter(CrawlLog.province_code == p.code)
            .order_by(desc(CrawlLog.created_at))
            .first()
        )
        province_stats.append({
            "province_code": p.code,
            "province_name": p.name,
            "schools": school_count,
            "majors": major_count,
            "course_links": link_count,
            "last_crawl": last_crawl.created_at.isoformat() if last_crawl else None,
            "last_crawl_status": last_crawl.status if last_crawl else None,
        })

    return {
        "code": 0,
        "data": {
            "total_provinces": len(provinces),
            "total_schools": db.query(School).count(),
            "total_majors": db.query(Major).count(),
            "total_course_links": db.query(MajorSubject).count(),
            "provinces": province_stats,
        },
    }


# ------------------------------------------------------------------
# Trigger crawl
# ------------------------------------------------------------------

class CrawlTriggerRequest(BaseModel):
    province_codes: list[str]
    source: str = "zikaosw"


ALLOWED_SOURCES = {"zikaosw"}


def _run_crawl_background(province_codes: list, source: str):
    """Run crawl in a subprocess."""
    cmd = [
        sys.executable, "-m", "scripts.crawl_majors",
        "--province", *province_codes,
        "--source", source,
    ]
    try:
        subprocess.Popen(
            cmd,
            cwd=os.getcwd(),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception as e:
        import logging
        logging.getLogger(__name__).error(f"Failed to start crawl subprocess: {e}")


@router.post("/trigger")
async def trigger_crawl(
    body: CrawlTriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """手动触发爬取任务"""
    _require_admin(current_user)

    if not body.province_codes:
        raise HTTPException(status_code=422, detail="请指定至少一个省份代码")
    if len(body.province_codes) > 31:
        raise HTTPException(status_code=422, detail="一次最多爬取 31 个省份")
    if body.source not in ALLOWED_SOURCES:
        raise HTTPException(status_code=422, detail=f"不支持的数据源: {body.source}")
    # 验证省份代码格式
    for code in body.province_codes:
        if not re.match(r"^\d{2}$", code):
            raise HTTPException(status_code=422, detail=f"省份代码格式无效: {code}")

    background_tasks.add_task(_run_crawl_background, body.province_codes, body.source)

    return {
        "code": 0,
        "data": {
            "message": f"已启动爬取任务: {len(body.province_codes)} 个省份",
            "province_codes": body.province_codes,
            "source": body.source,
        },
    }


# ------------------------------------------------------------------
# Data validation
# ------------------------------------------------------------------

@router.get("/validate/{province_code}")
async def validate_province_data(
    province_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """校验某省数据完整性"""
    _require_admin(current_user)

    province = db.query(Province).filter(Province.code == province_code).first()
    if not province:
        raise HTTPException(status_code=404, detail="省份不存在")

    majors = db.query(Major).filter(Major.province_id == province.id).all()
    issues = []

    for major in majors:
        # Check major has courses
        link_count = db.query(MajorSubject).filter(MajorSubject.major_id == major.id).count()
        if link_count == 0:
            issues.append({
                "type": "no_courses",
                "major_id": major.id,
                "major_name": f"{major.code} {major.name}",
                "message": "专业无关联课程",
            })
        elif link_count < 5:
            issues.append({
                "type": "few_courses",
                "major_id": major.id,
                "major_name": f"{major.code} {major.name}",
                "message": f"课程数偏少 ({link_count}门)",
            })

        # Check major code
        if not major.code or major.code.startswith("UNKNOWN"):
            issues.append({
                "type": "missing_code",
                "major_id": major.id,
                "major_name": major.name,
                "message": "缺少专业代码",
            })

    return {
        "code": 0,
        "data": {
            "province": province.name,
            "total_majors": len(majors),
            "issues_count": len(issues),
            "issues": issues,
            "is_valid": len(issues) == 0,
        },
    }
