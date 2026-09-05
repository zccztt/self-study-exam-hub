# -*- coding: utf-8 -*-
"""文件上传 API - 支持用户上传 PDF 学习资料"""

import hashlib
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.dependencies import get_current_user, get_db
from backend.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

# Use absolute path based on project root for consistent file storage
UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB
UPLOAD_CHUNK_SIZE = 1024 * 1024
MAX_EXTRACTED_TEXT_LENGTH = 50_000
MAX_PDF_PAGES = 100


@router.post("")
def upload_file(
    file: UploadFile = File(...),
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """上传学习资料文件（PDF/TXT/MD/DOCX），解析后纳入个人知识库。"""
    if not file.filename:
        raise HTTPException(400, "文件名不能为空")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"不支持的文件类型: {ext}，仅支持 {', '.join(ALLOWED_EXTENSIONS)}")

    temp_path: Optional[Path] = None
    file_size = 0
    hasher = hashlib.sha256()
    try:
        with tempfile.NamedTemporaryFile(mode="wb", delete=False, dir=UPLOAD_DIR, suffix=ext) as temp_file:
            temp_path = Path(temp_file.name)
            while chunk := file.file.read(UPLOAD_CHUNK_SIZE):
                file_size += len(chunk)
                if file_size > MAX_FILE_SIZE:
                    raise HTTPException(400, f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)")
                hasher.update(chunk)
                temp_file.write(chunk)
    except HTTPException:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        raise
    except OSError as exc:
        if temp_path:
            temp_path.unlink(missing_ok=True)
        raise HTTPException(500, "文件保存失败") from exc

    file_hash = hasher.hexdigest()[:16]
    save_path = UPLOAD_DIR / f"{current_user.id}_{file_hash}{ext}"
    created_file = not save_path.exists()
    try:
        if created_file:
            temp_path.replace(save_path)
        else:
            temp_path.unlink(missing_ok=True)
    except OSError as exc:
        temp_path.unlink(missing_ok=True)
        raise HTTPException(500, "文件保存失败") from exc

    extracted_text = _extract_file_text(save_path, ext)
    extraction_warning = None
    if not extracted_text:
        extraction_warning = "文件内容提取失败，文档已保存但无法用于智能搜索。"
        logger.warning("Text extraction returned empty for file: %s (ext=%s)", save_path, ext)

    # 保存到用户知识库
    from backend.models.knowledge import UserDocument

    doc = UserDocument(
        user_id=current_user.id,
        filename=file.filename,
        file_path=str(save_path),
        file_hash=file_hash,
        file_size=file_size,
        content_text=extracted_text,
        subject_id=subject_id,
    )
    try:
        db.add(doc)
        db.commit()
        db.refresh(doc)
    except Exception:
        db.rollback()
        if created_file:
            save_path.unlink(missing_ok=True)
        raise

    return {
        "id": doc.id,
        "filename": file.filename,
        "size": file_size,
        "extracted_length": len(extracted_text),
        "subject_id": subject_id,
        "warning": extraction_warning,
    }


@router.get("")
def list_my_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """列出我上传的文档"""
    from backend.models.knowledge import UserDocument

    docs = (
        db.query(UserDocument)
        .filter(UserDocument.user_id == current_user.id)
        .order_by(UserDocument.created_at.desc())
        .all()
    )
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_size": d.file_size,
            "subject_id": d.subject_id,
            "created_at": d.created_at.isoformat() if d.created_at else "",
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除我的文档"""
    from backend.models.knowledge import UserDocument

    doc = db.query(UserDocument).filter(
        UserDocument.id == doc_id,
        UserDocument.user_id == current_user.id,
    ).first()
    if not doc:
        raise HTTPException(404, "文档不存在")

    # 同一用户重复上传相同内容时会共享文件，只在最后一条记录删除后清理文件。
    file_path = Path(doc.file_path)
    shared_file_count = (
        db.query(UserDocument)
        .filter(UserDocument.file_path == doc.file_path, UserDocument.id != doc.id)
        .count()
    )
    db.delete(doc)
    db.commit()
    if shared_file_count == 0 and file_path.exists():
        file_path.unlink()
    return {"status": "deleted"}


def _extract_file_text(path: Path, ext: str) -> str:
    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext == ".docx":
        return _extract_docx_text(path)
    if ext in (".txt", ".md"):
        try:
            with path.open("r", encoding="utf-8", errors="ignore") as text_file:
                return text_file.read(MAX_EXTRACTED_TEXT_LENGTH)
        except OSError:
            return ""
    return ""


def _extract_pdf_text(path: Path) -> str:
    """从 PDF 文件提取文本内容"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(str(path))
        texts = []
        extracted_length = 0
        for page in reader.pages[:MAX_PDF_PAGES]:
            text = page.extract_text()
            if text:
                remaining = MAX_EXTRACTED_TEXT_LENGTH - extracted_length
                if remaining <= 0:
                    break
                part = text[:remaining]
                texts.append(part)
                extracted_length += len(part)
        return "\n".join(texts)[:MAX_EXTRACTED_TEXT_LENGTH]
    except ImportError:
        logger.warning("pypdf not installed, cannot extract PDF text from %s", path)
        return ""
    except Exception as exc:
        logger.warning("PDF text extraction failed for %s: %s", path, exc)
        return ""


def _extract_docx_text(path: Path) -> str:
    """从 DOCX 文件提取有限长度的纯文本。"""
    try:
        with zipfile.ZipFile(path) as archive:
            xml_content = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_content)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        extracted_length = 0
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(node.text or "" for node in paragraph.findall(".//w:t", namespace)).strip()
            if not text:
                continue
            remaining = MAX_EXTRACTED_TEXT_LENGTH - extracted_length
            if remaining <= 0:
                break
            part = text[:remaining]
            paragraphs.append(part)
            extracted_length += len(part) + 1
        return "\n".join(paragraphs)[:MAX_EXTRACTED_TEXT_LENGTH]
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError):
        return ""
