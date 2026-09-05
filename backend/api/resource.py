# -*- coding: utf-8 -*-
"""资源管理 API —— 上传文件(MinIO)、添加外部链接、挂载到题目/真题卷源。"""

import hashlib
import logging
import mimetypes
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db
from backend.minio_client import minio_client
from backend.models.question import Question
from backend.models.past_paper_source import PastPaperSource
from backend.models.resource import PaperSourceResource, QuestionResource, Resource
from backend.models.user import User
from backend.services.ocr_service import compute_file_hash, process_resource_ocr

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/resources", tags=["resources"])

MAX_FILE_SIZE = 50 * 1024 * 1024  # 50 MB
UPLOAD_CHUNK_SIZE = 1024 * 1024  # 1 MB

# 本地回退存储目录（MinIO 不可用时使用）
LOCAL_RESOURCE_DIR = Path(__file__).resolve().parent.parent.parent / "uploads" / "resources"
LOCAL_RESOURCE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {
    # PDF
    ".pdf": "pdf",
    # 图片
    ".jpg": "image", ".jpeg": "image", ".png": "image",
    ".gif": "image", ".bmp": "image", ".webp": "image",
    # 文档
    ".docx": "doc", ".txt": "doc", ".md": "doc",
}


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class LinkCreateRequest(BaseModel):
    url: str
    title: str = ""
    media_type: str = "video"  # video / pdf / image / doc


class AttachRequest(BaseModel):
    resource_id: int
    sort_order: int = 0


# ---------------------------------------------------------------------------
# 上传文件
# ---------------------------------------------------------------------------

@router.post("/upload")
def upload_resource(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传文件到 MinIO（或本地回退），创建 Resource 记录，后台执行 OCR。"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    media_type = ALLOWED_EXTENSIONS.get(ext)
    if not media_type:
        raise HTTPException(
            400,
            f"不支持的文件类型: {ext}，支持 {', '.join(sorted(ALLOWED_EXTENSIONS.keys()))}",
        )

    # 流式读取 + 计算哈希
    chunks = []
    file_size = 0
    hasher = hashlib.sha256()
    while True:
        chunk = file.file.read(UPLOAD_CHUNK_SIZE)
        if not chunk:
            break
        file_size += len(chunk)
        if file_size > MAX_FILE_SIZE:
            raise HTTPException(400, f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")
        hasher.update(chunk)
        chunks.append(chunk)

    file_data = b"".join(chunks)
    file_hash = hasher.hexdigest()[:16]

    # 去重：同 hash 的文件复用已有存储对象
    existing = db.query(Resource).filter(
        Resource.file_hash == file_hash,
        Resource.storage_type.in_(["minio", "local"]),
    ).first()

    if existing:
        minio_object = existing.minio_object
        storage_type = existing.storage_type
    else:
        now = datetime.now(timezone.utc)
        safe_name = Path(file.filename).name.replace(" ", "_")
        object_path = f"resources/{media_type}/{now.year}/{now.month:02d}/{file_hash}_{safe_name}"

        content_type_val = mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

        if minio_client.is_available:
            ok = minio_client.upload_file(object_path, file_data, content_type_val)
            if not ok:
                raise HTTPException(500, "文件上传到存储服务失败")
            minio_object = object_path
            storage_type = "minio"
        else:
            # MinIO 不可用时回退到本地存储
            local_path = LOCAL_RESOURCE_DIR / f"{file_hash}_{safe_name}"
            local_path.write_bytes(file_data)
            minio_object = str(local_path)
            storage_type = "local"
            logger.warning("MinIO unavailable, saved resource to local: %s", local_path)

    # 创建 Resource 记录
    resource = Resource(
        filename=file.filename,
        media_type=media_type,
        storage_type=storage_type,
        minio_object=minio_object,
        content_type=mimetypes.guess_type(file.filename)[0] or "application/octet-stream",
        file_size=file_size,
        file_hash=file_hash,
        ocr_status="pending",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)

    # 后台 OCR
    background_tasks.add_task(process_resource_ocr, resource.id, file_data)

    return {
        "id": resource.id,
        "filename": resource.filename,
        "media_type": resource.media_type,
        "file_size": resource.file_size,
        "ocr_status": resource.ocr_status,
    }


# ---------------------------------------------------------------------------
# 创建外部链接（视频等）
# ---------------------------------------------------------------------------

@router.post("/link")
def create_link_resource(
    body: LinkCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建外部链接资源（视频、外部 PDF 等）。"""
    resource = Resource(
        filename=body.title or body.url,
        media_type=body.media_type,
        storage_type="external_link",
        external_url=body.url,
        ocr_status="skipped",
    )
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return {
        "id": resource.id,
        "filename": resource.filename,
        "media_type": resource.media_type,
        "external_url": resource.external_url,
        "ocr_status": resource.ocr_status,
    }


# ---------------------------------------------------------------------------
# 查看 / 删除
# ---------------------------------------------------------------------------

@router.get("/{resource_id}")
def get_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取资源详情（MinIO 资源附带预签名下载 URL）。"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "资源不存在")

    download_url = None
    if resource.storage_type == "minio" and resource.minio_object:
        download_url = minio_client.get_presigned_url(resource.minio_object)

    return {
        "id": resource.id,
        "filename": resource.filename,
        "media_type": resource.media_type,
        "storage_type": resource.storage_type,
        "external_url": resource.external_url,
        "download_url": download_url,
        "content_type": resource.content_type,
        "file_size": resource.file_size,
        "ocr_status": resource.ocr_status,
        "has_content_text": bool(resource.content_text),
        "created_at": resource.created_at.isoformat() if resource.created_at else None,
    }


@router.get("/{resource_id}/content")
def get_resource_content(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取资源的 OCR / 提取文字。"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "资源不存在")
    return {
        "id": resource.id,
        "ocr_status": resource.ocr_status,
        "content_text": resource.content_text,
    }


@router.delete("/{resource_id}")
def delete_resource(
    resource_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除资源（MinIO 对象 + DB 记录 + 关联）。"""
    resource = db.query(Resource).filter(Resource.id == resource_id).first()
    if not resource:
        raise HTTPException(404, "资源不存在")

    # 仅当没有其他 Resource 共享同一 MinIO 对象时才删除存储
    if resource.storage_type == "minio" and resource.minio_object:
        shared = (
            db.query(Resource)
            .filter(
                Resource.minio_object == resource.minio_object,
                Resource.id != resource.id,
            )
            .count()
        )
        if shared == 0:
            minio_client.delete_file(resource.minio_object)
            if resource.thumbnail_object:
                minio_client.delete_file(resource.thumbnail_object)

    # 删除关联
    db.query(QuestionResource).filter(QuestionResource.resource_id == resource_id).delete()
    db.query(PaperSourceResource).filter(PaperSourceResource.resource_id == resource_id).delete()
    db.delete(resource)
    db.commit()
    return {"status": "deleted"}


# ---------------------------------------------------------------------------
# 挂载 / 取消挂载到题目
# ---------------------------------------------------------------------------

@router.post("/{resource_id}/attach/question/{question_id}")
def attach_to_question(
    resource_id: int,
    question_id: int,
    sort_order: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将资源挂载到题目。"""
    _ensure_exists(db, Resource, resource_id, "资源")
    _ensure_exists(db, Question, question_id, "题目")

    exists = (
        db.query(QuestionResource)
        .filter(
            QuestionResource.question_id == question_id,
            QuestionResource.resource_id == resource_id,
        )
        .first()
    )
    if exists:
        exists.sort_order = sort_order
        db.commit()
        return {"status": "updated"}

    link = QuestionResource(
        question_id=question_id,
        resource_id=resource_id,
        sort_order=sort_order,
    )
    db.add(link)
    db.commit()
    return {"status": "attached"}


@router.delete("/{resource_id}/attach/question/{question_id}")
def detach_from_question(
    resource_id: int,
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消资源与题目的挂载。"""
    deleted = (
        db.query(QuestionResource)
        .filter(
            QuestionResource.question_id == question_id,
            QuestionResource.resource_id == resource_id,
        )
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(404, "该挂载关系不存在")
    return {"status": "detached"}


# ---------------------------------------------------------------------------
# 挂载 / 取消挂载到真题卷源
# ---------------------------------------------------------------------------

@router.post("/{resource_id}/attach/paper-source/{paper_source_id}")
def attach_to_paper_source(
    resource_id: int,
    paper_source_id: int,
    sort_order: int = Query(0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """将资源挂载到真题卷源。"""
    _ensure_exists(db, Resource, resource_id, "资源")
    _ensure_exists(db, PastPaperSource, paper_source_id, "真题卷源")

    exists = (
        db.query(PaperSourceResource)
        .filter(
            PaperSourceResource.paper_source_id == paper_source_id,
            PaperSourceResource.resource_id == resource_id,
        )
        .first()
    )
    if exists:
        exists.sort_order = sort_order
        db.commit()
        return {"status": "updated"}

    link = PaperSourceResource(
        paper_source_id=paper_source_id,
        resource_id=resource_id,
        sort_order=sort_order,
    )
    db.add(link)
    db.commit()
    return {"status": "attached"}


@router.delete("/{resource_id}/attach/paper-source/{paper_source_id}")
def detach_from_paper_source(
    resource_id: int,
    paper_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """取消资源与真题卷源的挂载。"""
    deleted = (
        db.query(PaperSourceResource)
        .filter(
            PaperSourceResource.paper_source_id == paper_source_id,
            PaperSourceResource.resource_id == resource_id,
        )
        .delete()
    )
    db.commit()
    if not deleted:
        raise HTTPException(404, "该挂载关系不存在")
    return {"status": "detached"}


# ---------------------------------------------------------------------------
# 列出某实体的资源
# ---------------------------------------------------------------------------

@router.get("/by-question/{question_id}")
def list_question_resources(
    question_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出题目的所有资源。"""
    rows = (
        db.query(Resource, QuestionResource.sort_order)
        .join(QuestionResource, QuestionResource.resource_id == Resource.id)
        .filter(QuestionResource.question_id == question_id)
        .order_by(QuestionResource.sort_order)
        .all()
    )
    return [_resource_summary(r, sort_order) for r, sort_order in rows]


@router.get("/by-paper-source/{paper_source_id}")
def list_paper_source_resources(
    paper_source_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出真题卷源的所有资源。"""
    rows = (
        db.query(Resource, PaperSourceResource.sort_order)
        .join(PaperSourceResource, PaperSourceResource.resource_id == Resource.id)
        .filter(PaperSourceResource.paper_source_id == paper_source_id)
        .order_by(PaperSourceResource.sort_order)
        .all()
    )
    return [_resource_summary(r, sort_order) for r, sort_order in rows]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ensure_exists(db: Session, model, record_id: int, label: str):
    if not db.query(model).filter(model.id == record_id).first():
        raise HTTPException(404, f"{label}不存在 (id={record_id})")


def _resource_summary(resource: Resource, sort_order: int = 0) -> dict:
    download_url = None
    if resource.storage_type == "minio" and resource.minio_object:
        download_url = minio_client.get_presigned_url(resource.minio_object)

    return {
        "id": resource.id,
        "filename": resource.filename,
        "media_type": resource.media_type,
        "storage_type": resource.storage_type,
        "external_url": resource.external_url,
        "download_url": download_url,
        "file_size": resource.file_size,
        "ocr_status": resource.ocr_status,
        "sort_order": sort_order,
    }
