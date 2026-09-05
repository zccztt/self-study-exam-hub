# -*- coding: utf-8 -*-
"""Admin management API routes."""

import csv
import io
import json
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import func, insert
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user
from backend.database import get_db
from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.exam import ExamSession, WrongQuestion
from backend.models.question import Question
from backend.models.subject import Subject
from backend.models.user import User
from backend.models.video import Video
from backend.utils import hash_password

router = APIRouter(prefix="/admin", tags=["admin"])

QUESTION_IMPORT_BATCH_SIZE = 500
MAX_QUESTION_IMPORT_FILE_SIZE = 50 * 1024 * 1024
MAX_IMPORT_ERRORS = 20


# ─── Admin Guard ───────────────────────────────────────────────────────────────

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限。")
    return current_user


# ─── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
async def dashboard(db: Session = Depends(get_db), _: User = Depends(require_admin)):
    return {
        "code": 0,
        "data": {
            "user_count": db.query(func.count(User.id)).scalar(),
            "subject_count": db.query(func.count(Subject.id)).scalar(),
            "question_count": db.query(func.count(Question.id)).scalar(),
            "video_count": db.query(func.count(Video.id)).scalar(),
            "chapter_count": db.query(func.count(Chapter.id)).scalar(),
            "exam_session_count": db.query(func.count(ExamSession.id)).scalar(),
        },
    }


# ─── User Management ──────────────────────────────────────────────────────────


class UserUpdateRequest(BaseModel):
    email: Optional[str] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None
    is_superuser: Optional[bool] = None


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    email: str = Field(min_length=5, max_length=120)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    is_superuser: bool = False


@router.get("/users")
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(User)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(User.username.ilike(pattern) | User.email.ilike(pattern))
    total = query.count()
    users = query.order_by(User.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_serialize_user(u) for u in users],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/users")
async def create_user(
    body: UserCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在。")
    if db.query(User).filter(User.email == body.email.strip().lower()).first():
        raise HTTPException(status_code=400, detail="邮箱已被注册。")
    user = User(
        username=body.username,
        email=body.email.strip().lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_superuser=body.is_superuser,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"code": 0, "data": _serialize_user(user)}


@router.put("/users/{user_id}")
async def update_user(
    user_id: int,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在。")
    if body.email is not None:
        user.email = body.email.strip().lower()
    if body.full_name is not None:
        user.full_name = body.full_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_superuser is not None:
        user.is_superuser = body.is_superuser
    db.commit()
    db.refresh(user)
    return {"code": 0, "data": _serialize_user(user)}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除自己的账号。")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在。")
    db.delete(user)
    db.commit()
    return {"code": 0, "data": {"success": True}}


def _serialize_user(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "is_active": user.is_active,
        "is_superuser": user.is_superuser,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


# ─── Subject Management ───────────────────────────────────────────────────────


class SubjectRequest(BaseModel):
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=100)
    category: str = Field(default="public", max_length=50)
    description: Optional[str] = None
    exam_duration: int = Field(default=150, ge=30, le=300)
    total_score: int = Field(default=100, ge=1)


@router.get("/subjects")
async def list_subjects(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Subject)
    if keyword:
        pattern = f"%{keyword.strip()}%"
        query = query.filter(Subject.name.ilike(pattern) | Subject.code.ilike(pattern))
    total = query.count()
    items = query.order_by(Subject.id).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_serialize_subject(s) for s in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/subjects")
async def create_subject(
    body: SubjectRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    if db.query(Subject).filter(Subject.code == body.code).first():
        raise HTTPException(status_code=400, detail="科目代码已存在。")
    subject = Subject(**body.model_dump())
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return {"code": 0, "data": _serialize_subject(subject)}


@router.put("/subjects/{subject_id}")
async def update_subject(
    subject_id: int,
    body: SubjectRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在。")
    dup = db.query(Subject).filter(Subject.code == body.code, Subject.id != subject_id).first()
    if dup:
        raise HTTPException(status_code=400, detail="科目代码已被其他科目使用。")
    for key, value in body.model_dump().items():
        setattr(subject, key, value)
    db.commit()
    db.refresh(subject)
    return {"code": 0, "data": _serialize_subject(subject)}


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    subject = db.query(Subject).filter(Subject.id == subject_id).first()
    if not subject:
        raise HTTPException(status_code=404, detail="科目不存在。")
    q_count = db.query(func.count(Question.id)).filter(Question.subject_id == subject_id).scalar()
    if q_count > 0:
        raise HTTPException(status_code=400, detail=f"科目下尚有 {q_count} 道题目，无法删除。请先清空题目。")
    db.delete(subject)
    db.commit()
    return {"code": 0, "data": {"success": True}}


def _serialize_subject(s: Subject) -> dict:
    return {
        "id": s.id,
        "code": s.code,
        "name": s.name,
        "category": s.category,
        "description": s.description,
        "exam_duration": s.exam_duration,
        "total_score": s.total_score,
        "created_at": s.created_at.isoformat() if s.created_at else None,
    }


# ─── Question Management ──────────────────────────────────────────────────────


class QuestionRequest(BaseModel):
    subject_id: int
    content: str = Field(min_length=1)
    question_type: str
    options: Optional[Any] = None
    answer: str = Field(min_length=1)
    explanation: Optional[str] = None
    year: Optional[int] = None
    month: Optional[int] = None
    chapter_id: Optional[int] = None
    difficulty: str = "medium"
    score: int = Field(default=2, ge=1)


@router.get("/questions")
async def list_questions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject_id: Optional[int] = None,
    question_type: Optional[str] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Question)
    if subject_id:
        query = query.filter(Question.subject_id == subject_id)
    if question_type:
        query = query.filter(Question.question_type == question_type)
    if keyword:
        query = query.filter(Question.content.ilike(f"%{keyword.strip()}%"))
    total = query.count()
    items = query.order_by(Question.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_serialize_question(q) for q in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/questions")
async def create_question(
    body: QuestionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    question = Question(**body.model_dump())
    db.add(question)
    db.commit()
    db.refresh(question)
    return {"code": 0, "data": _serialize_question(question)}


@router.put("/questions/{question_id}")
async def update_question(
    question_id: int,
    body: QuestionRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在。")
    for key, value in body.model_dump().items():
        setattr(question, key, value)
    db.commit()
    db.refresh(question)
    return {"code": 0, "data": _serialize_question(question)}


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    question = db.query(Question).filter(Question.id == question_id).first()
    if not question:
        raise HTTPException(status_code=404, detail="题目不存在。")
    db.query(QuestionKnowledgePoint).filter(QuestionKnowledgePoint.question_id == question_id).delete()
    db.query(WrongQuestion).filter(WrongQuestion.question_id == question_id).delete()
    db.delete(question)
    db.commit()
    return {"code": 0, "data": {"success": True}}


@router.post("/questions/import")
def import_questions(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """批量导入题目，支持 JSON 和 CSV 格式。"""
    filename = (file.filename or "").lower()
    if not filename.endswith((".json", ".csv")):
        raise HTTPException(status_code=400, detail="仅支持 .json 和 .csv 格式文件。")

    file.file.seek(0, io.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > MAX_QUESTION_IMPORT_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"导入文件不能超过 {MAX_QUESTION_IMPORT_FILE_SIZE // 1024 // 1024}MB。",
        )

    imported = 0
    errors: List[str] = []
    batch: List[Dict[str, Any]] = []

    def flush_batch() -> None:
        if batch:
            db.execute(insert(Question), batch)
            batch.clear()

    def add_record(record: Dict[str, Any], label: str) -> None:
        nonlocal imported
        try:
            batch.append(_build_question_import_mapping(record))
            imported += 1
            if len(batch) >= QUESTION_IMPORT_BATCH_SIZE:
                flush_batch()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if len(errors) < MAX_IMPORT_ERRORS:
                errors.append(f"{label}：{exc}")

    try:
        text_stream = io.TextIOWrapper(file.file, encoding="utf-8-sig", newline="")
        try:
            if filename.endswith(".json"):
                try:
                    records = json.load(text_stream)
                except json.JSONDecodeError as exc:
                    raise HTTPException(status_code=400, detail=f"JSON 解析失败：{exc}") from exc
                if not isinstance(records, list):
                    raise HTTPException(status_code=400, detail="JSON 顶层必须是题目数组。")
                for index, record in enumerate(records, start=1):
                    if not isinstance(record, dict):
                        if len(errors) < MAX_IMPORT_ERRORS:
                            errors.append(f"第 {index} 条：必须是 JSON 对象")
                        continue
                    add_record(record, f"第 {index} 条")
            else:
                for line_number, row in enumerate(csv.DictReader(text_stream), start=2):
                    add_record(row, f"第 {line_number} 行")
        finally:
            text_stream.detach()

        flush_batch()
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except UnicodeDecodeError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail="文件必须使用 UTF-8 编码。") from exc
    except Exception:
        db.rollback()
        raise

    return {"code": 0, "data": {"imported": imported, "errors": errors}}


def _build_question_import_mapping(record: Dict[str, Any]) -> Dict[str, Any]:
    options = record.get("options")
    if isinstance(options, str):
        options = json.loads(options) if options.strip() else None

    return {
        "subject_id": int(record["subject_id"]),
        "content": str(record["content"]),
        "question_type": str(record["question_type"]),
        "options": options,
        "answer": str(record["answer"]),
        "explanation": record.get("explanation"),
        "year": int(record["year"]) if record.get("year") not in (None, "") else None,
        "month": int(record["month"]) if record.get("month") not in (None, "") else None,
        "chapter_id": int(record["chapter_id"]) if record.get("chapter_id") not in (None, "") else None,
        "difficulty": record.get("difficulty") or "medium",
        "score": int(record.get("score") or 2),
    }


def _serialize_question(q: Question) -> dict:
    return {
        "id": q.id,
        "subject_id": q.subject_id,
        "content": q.content[:200] if q.content else "",
        "question_type": q.question_type,
        "options": q.options,
        "answer": q.answer,
        "explanation": q.explanation,
        "year": q.year,
        "month": q.month,
        "chapter_id": q.chapter_id,
        "difficulty": q.difficulty,
        "frequency": q.frequency,
        "score": q.score,
        "created_at": q.created_at.isoformat() if q.created_at else None,
    }


# ─── Video Management ─────────────────────────────────────────────────────────


class VideoRequest(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    url: str = Field(min_length=1, max_length=500)
    source: str = Field(default="custom", max_length=32)
    duration: Optional[int] = None
    author: Optional[str] = None
    subject_id: int
    chapter_id: Optional[int] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("/videos")
async def list_videos(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    subject_id: Optional[int] = None,
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Video)
    if subject_id:
        query = query.filter(Video.subject_id == subject_id)
    if keyword:
        query = query.filter(Video.title.ilike(f"%{keyword.strip()}%"))
    total = query.count()
    items = query.order_by(Video.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {
        "code": 0,
        "data": {
            "items": [_serialize_video(v) for v in items],
            "total": total,
            "page": page,
            "page_size": page_size,
        },
    }


@router.post("/videos")
async def create_video(
    body: VideoRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    video = Video(**body.model_dump())
    db.add(video)
    db.commit()
    db.refresh(video)
    return {"code": 0, "data": _serialize_video(video)}


@router.put("/videos/{video_id}")
async def update_video(
    video_id: int,
    body: VideoRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在。")
    for key, value in body.model_dump().items():
        setattr(video, key, value)
    db.commit()
    db.refresh(video)
    return {"code": 0, "data": _serialize_video(video)}


@router.delete("/videos/{video_id}")
async def delete_video(
    video_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    video = db.query(Video).filter(Video.id == video_id).first()
    if not video:
        raise HTTPException(status_code=404, detail="视频不存在。")
    db.delete(video)
    db.commit()
    return {"code": 0, "data": {"success": True}}


def _serialize_video(v: Video) -> dict:
    return {
        "id": v.id,
        "title": v.title,
        "url": v.url,
        "source": v.source,
        "duration": v.duration,
        "author": v.author,
        "subject_id": v.subject_id,
        "chapter_id": v.chapter_id,
        "description": v.description,
        "tags": v.tags,
        "is_active": v.is_active,
        "created_at": v.created_at.isoformat() if v.created_at else None,
    }


# ─── Chapter Management ───────────────────────────────────────────────────────


class ChapterRequest(BaseModel):
    subject_id: int
    name: str = Field(min_length=1, max_length=200)
    order: int = Field(default=0, ge=0)
    parent_id: Optional[int] = None
    description: Optional[str] = None


@router.get("/chapters")
async def list_chapters(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(Chapter)
    if subject_id:
        query = query.filter(Chapter.subject_id == subject_id)
    items = query.order_by(Chapter.subject_id, Chapter.order, Chapter.id).all()
    return {
        "code": 0,
        "data": [_serialize_chapter(c) for c in items],
    }


@router.post("/chapters")
async def create_chapter(
    body: ChapterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    chapter = Chapter(**body.model_dump())
    db.add(chapter)
    db.commit()
    db.refresh(chapter)
    return {"code": 0, "data": _serialize_chapter(chapter)}


@router.put("/chapters/{chapter_id}")
async def update_chapter(
    chapter_id: int,
    body: ChapterRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在。")
    for key, value in body.model_dump().items():
        setattr(chapter, key, value)
    db.commit()
    db.refresh(chapter)
    return {"code": 0, "data": _serialize_chapter(chapter)}


@router.delete("/chapters/{chapter_id}")
async def delete_chapter(
    chapter_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
    if not chapter:
        raise HTTPException(status_code=404, detail="章节不存在。")
    q_count = db.query(func.count(Question.id)).filter(Question.chapter_id == chapter_id).scalar()
    if q_count > 0:
        raise HTTPException(status_code=400, detail=f"章节下有 {q_count} 道题目，无法删除。")
    db.delete(chapter)
    db.commit()
    return {"code": 0, "data": {"success": True}}


def _serialize_chapter(c: Chapter) -> dict:
    return {
        "id": c.id,
        "subject_id": c.subject_id,
        "name": c.name,
        "order": c.order,
        "parent_id": c.parent_id,
        "description": c.description,
    }
