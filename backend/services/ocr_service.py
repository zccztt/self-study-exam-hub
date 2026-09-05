# -*- coding: utf-8 -*-
"""OCR / 文字提取服务 —— PDF、图片、DOCX、纯文本。"""

import hashlib
import io
import logging
import tempfile
import zipfile
from pathlib import Path
from typing import Optional
from xml.etree import ElementTree

from sqlalchemy.orm import Session

from backend.database import SessionLocal
from backend.models.resource import Resource

logger = logging.getLogger(__name__)

MAX_EXTRACTED_TEXT_LENGTH = 50_000
MAX_PDF_PAGES = 100
MIN_TEXT_FOR_SKIP_OCR = 100  # PDF 文字层超过此字数则跳过 OCR


# ---------------------------------------------------------------------------
# 公共入口 —— 作为 FastAPI BackgroundTask 调用
# ---------------------------------------------------------------------------

def process_resource_ocr(resource_id: int, file_data: bytes) -> None:
    """后台任务：对资源执行文字提取 / OCR，结果写回 DB。

    该函数在独立线程中运行，自行管理数据库会话。
    """
    db: Session = SessionLocal()
    try:
        resource = db.query(Resource).filter(Resource.id == resource_id).first()
        if resource is None:
            logger.warning("process_resource_ocr: resource %s not found", resource_id)
            return

        resource.ocr_status = "processing"
        db.commit()

        text = ""
        media = resource.media_type

        try:
            if media == "pdf":
                text = _extract_pdf(file_data)
            elif media == "image":
                text = _ocr_image(file_data)
            elif media == "doc":
                text = _extract_doc(file_data, resource.filename or "")
            else:
                # video / unknown → 跳过
                resource.ocr_status = "skipped"
                db.commit()
                return

            resource.content_text = text[:MAX_EXTRACTED_TEXT_LENGTH] if text else None
            resource.ocr_status = "completed" if text else "failed"
        except Exception as exc:
            logger.exception("OCR failed for resource %s: %s", resource_id, exc)
            resource.ocr_status = "failed"

        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


# ---------------------------------------------------------------------------
# PDF 提取：先文字层，不足则 OCR
# ---------------------------------------------------------------------------

def _extract_pdf(file_data: bytes) -> str:
    """尝试从 PDF 提取文字；若文字层不足则回退到 OCR。"""
    text = _extract_pdf_text_layer(file_data)
    if len(text.strip()) >= MIN_TEXT_FOR_SKIP_OCR:
        return text

    # 文字层不足 → pdf2image + pytesseract OCR
    logger.info("PDF text layer insufficient (%d chars), falling back to OCR", len(text.strip()))
    ocr_text = _ocr_pdf_pages(file_data)
    return ocr_text if ocr_text else text


def _extract_pdf_text_layer(file_data: bytes) -> str:
    """用 pypdf 提取 PDF 文字层。"""
    try:
        from pypdf import PdfReader

        reader = PdfReader(io.BytesIO(file_data))
        texts = []
        extracted_length = 0
        for page in reader.pages[:MAX_PDF_PAGES]:
            page_text = page.extract_text()
            if page_text:
                remaining = MAX_EXTRACTED_TEXT_LENGTH - extracted_length
                if remaining <= 0:
                    break
                part = page_text[:remaining]
                texts.append(part)
                extracted_length += len(part)
        return "\n".join(texts)
    except ImportError:
        logger.warning("pypdf not installed, skipping PDF text layer extraction")
        return ""
    except Exception as exc:
        logger.warning("PDF text layer extraction failed: %s", exc)
        return ""


def _ocr_pdf_pages(file_data: bytes) -> str:
    """将 PDF 页面转为图片后 OCR。需要 pdf2image + pytesseract。"""
    try:
        from pdf2image import convert_from_bytes
        import pytesseract

        images = convert_from_bytes(
            file_data,
            dpi=200,
            first_page=1,
            last_page=min(MAX_PDF_PAGES, 999),
        )
        texts = []
        extracted_length = 0
        for img in images:
            page_text = pytesseract.image_to_string(img, lang="chi_sim+eng")
            if page_text:
                remaining = MAX_EXTRACTED_TEXT_LENGTH - extracted_length
                if remaining <= 0:
                    break
                part = page_text[:remaining]
                texts.append(part)
                extracted_length += len(part)
        return "\n".join(texts)
    except ImportError as exc:
        logger.warning("pdf2image or pytesseract not installed, skipping PDF OCR: %s", exc)
        return ""
    except Exception as exc:
        logger.warning("PDF OCR failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# 图片 OCR
# ---------------------------------------------------------------------------

def _ocr_image(file_data: bytes) -> str:
    """对图片执行 OCR。"""
    try:
        import pytesseract
        from PIL import Image

        img = Image.open(io.BytesIO(file_data))
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text[:MAX_EXTRACTED_TEXT_LENGTH] if text else ""
    except ImportError as exc:
        logger.warning("pytesseract/pillow not installed: %s", exc)
        return ""
    except Exception as exc:
        logger.warning("Image OCR failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# DOCX / TXT / MD 文字提取
# ---------------------------------------------------------------------------

def _extract_doc(file_data: bytes, filename: str) -> str:
    """根据文件后缀提取文字。"""
    ext = Path(filename).suffix.lower()
    if ext == ".docx":
        return _extract_docx_text(file_data)
    if ext in (".txt", ".md"):
        return file_data.decode("utf-8", errors="ignore")[:MAX_EXTRACTED_TEXT_LENGTH]
    return ""


def _extract_docx_text(file_data: bytes) -> str:
    """从 DOCX 字节流提取纯文本。"""
    try:
        with zipfile.ZipFile(io.BytesIO(file_data)) as archive:
            xml_content = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_content)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        extracted_length = 0
        for paragraph in root.findall(".//w:p", namespace):
            text = "".join(
                node.text or "" for node in paragraph.findall(".//w:t", namespace)
            ).strip()
            if not text:
                continue
            remaining = MAX_EXTRACTED_TEXT_LENGTH - extracted_length
            if remaining <= 0:
                break
            part = text[:remaining]
            paragraphs.append(part)
            extracted_length += len(part) + 1
        return "\n".join(paragraphs)[:MAX_EXTRACTED_TEXT_LENGTH]
    except (OSError, KeyError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
        logger.warning("DOCX text extraction failed: %s", exc)
        return ""


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def compute_file_hash(file_data: bytes) -> str:
    """返回文件内容的 SHA-256 前 16 位十六进制。"""
    return hashlib.sha256(file_data).hexdigest()[:16]
