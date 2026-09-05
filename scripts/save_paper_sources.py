# -*- coding: utf-8 -*-
"""Discover and persist real-paper source links via the Tavily pool.

Only sources with extractable question text are imported as questions. PDF and
image links that cannot be parsed, plus every video result, remain available in
``past_paper_sources`` for manual review or a later retry.
"""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Chapter, PastPaper, PastPaperSource, Province, Question, Subject
from backend.services.search_client import SearchResult, search_client
from scripts.parse_paper import parse_paper_text


VIDEO_HOSTS = ("bilibili.com", "youtube.com", "youtu.be", "v.qq.com", "douyin.com")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
PDF_EXTENSIONS = (".pdf",)


def media_type(result: SearchResult) -> str:
    url = result.url.lower().split("?", 1)[0]
    host = urlparse(url).netloc
    if any(token in host for token in VIDEO_HOSTS):
        return "video"
    if url.endswith(PDF_EXTENSIONS):
        return "pdf"
    if url.endswith(IMAGE_EXTENSIONS):
        return "image"
    if any(token in result.title.lower() for token in (".pdf", "pdf", "试题图片", "试卷图片")):
        return "pdf" if "pdf" in result.title.lower() else "image"
    return "html"


def infer_period(text: str) -> tuple[int | None, int | None]:
    match = re.search(r"(20\d{2})年\s*(4|10)月", text)
    return (int(match.group(1)), int(match.group(2))) if match else (None, None)


def extract_source(result: SearchResult, kind: str) -> tuple[str | None, str | None]:
    """Return extracted text and an error message without raising."""
    if kind == "video":
        return None, "视频来源按要求仅保存链接"
    if kind == "pdf" or result.url.lower().split("?", 1)[0].endswith(".pdf"):
        try:
            import httpx
            from pypdf import PdfReader

            response = httpx.get(result.url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
                handle.write(response.content)
                path = Path(handle.name)
            try:
                text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
            finally:
                path.unlink(missing_ok=True)
            if text.strip():
                return text, None
            return None, "PDF 无文本层，需人工 OCR"
        except Exception as exc:
            return None, f"PDF 解析失败: {type(exc).__name__}"
    if kind == "image":
        try:
            import io
            import httpx
            from PIL import Image
            import pytesseract

            response = httpx.get(result.url, follow_redirects=True, timeout=30)
            response.raise_for_status()
            text = pytesseract.image_to_string(Image.open(io.BytesIO(response.content)), lang="chi_sim+eng")
            if text.strip():
                return text, None
            return None, "图片 OCR 未识别到文字"
        except ImportError:
            return None, "图片 OCR 依赖未安装，保留链接待人工识别"
        except Exception as exc:
            return None, f"图片 OCR 失败: {type(exc).__name__}"
    content = search_client.tavily_extract(result.url)
    if content and len(content.strip()) >= 200:
        return content, None
    return None, "正文抽取失败，保留链接待人工下载/OCR"


def import_questions(db, record: PastPaperSource, subject: Subject) -> int:
    """Parse extracted text and create a paper only when enough questions exist."""
    if not record.content_text or not record.year or not record.month:
        return 0
    text = record.content_text
    # Reject navigation/product pages before the generic numbered-line parser.
    # Real paper text should contain exam markers and several option labels;
    # this prevents prices, coupons and catalog entries becoming questions.
    exam_markers = sum(token in text for token in ("试题", "单项选择题", "多项选择题", "课程代码", "考试结束"))
    option_markers = len(re.findall(r"(?:^|\n)\s*[A-F][\.、．\)]", text))
    if exam_markers < 1 or option_markers < 4:
        record.error_message = "正文疑似目录/商品页，未满足试题标记与选项校验"
        return 0
    parsed = parse_paper_text(
        text,
        subject_code=subject.code,
        subject_name=subject.name,
        year=record.year,
        month=record.month,
        source=f"真实真题-来源链接-{record.url[:80]}",
        default_difficulty="medium",
    )
    if len(parsed) < 5:
        record.error_message = "已提取正文，但未达到 5 题结构化解析阈值"
        return 0
    chapters = db.query(Chapter).filter(Chapter.subject_id == subject.id).order_by(Chapter.order).all()
    question_ids = []
    for index, item in enumerate(parsed):
        existing = db.query(Question).filter(
            Question.subject_id == subject.id,
            Question.content == item["content"],
        ).first()
        if existing:
            question_ids.append(existing.id)
            continue
        question = Question(
            subject_id=subject.id,
            content=item["content"],
            question_type=item["question_type"],
            options=item.get("options") or [],
            answer=item.get("answer") or "待核实",
            explanation=item.get("explanation") or "来源文本已解析，答案待核实",
            year=record.year,
            month=record.month,
            chapter_id=chapters[index % len(chapters)].id if chapters else None,
            difficulty="medium",
            frequency=1,
            score=item.get("score") or 2,
            source=f"真实真题-来源链接-{record.url[:80]}",
            source_url=record.url,
        )
        db.add(question)
        db.flush()
        question_ids.append(question.id)
    province = db.query(Province).filter(Province.code == "13").first()
    paper = db.query(PastPaper).filter(
        PastPaper.subject_id == subject.id,
        PastPaper.year == record.year,
        PastPaper.month == record.month,
        PastPaper.source == f"真实真题-来源链接-{record.url[:80]}",
    ).first()
    if not paper:
        paper = PastPaper(
            subject_id=subject.id,
            name=f"{record.year}年{record.month}月 {subject.name} 真题（来源解析）",
            year=record.year,
            month=record.month,
            province_id=province.id if province else None,
            total_score=sum(q.get("score") or 2 for q in parsed),
            duration=150,
            question_ids=question_ids,
            paper_config={"source_url": record.url, "parsed_from_source": True},
            source=f"真实真题-来源链接-{record.url[:80]}",
            is_published=True,
        )
        db.add(paper)
        db.flush()
    record.parsed_question_count = len(question_ids)
    record.linked_paper_id = paper.id
    record.status = "parsed"
    return len(question_ids)


def save_result(db, result: SearchResult, subject: Subject | None, query: str) -> PastPaperSource:
    existing = db.query(PastPaperSource).filter(PastPaperSource.url == result.url).first()
    if existing:
        return existing
    year, month = infer_period(f"{result.title} {result.content} {query}")
    kind = media_type(result)
    record = PastPaperSource(
        subject_id=subject.id if subject else None,
        year=year,
        month=month,
        title=result.title or result.url,
        url=result.url,
        source=result.source or "tavily",
        media_type=kind,
        status="link_only" if kind == "video" else "pending",
        error_message="视频来源按要求仅保存链接" if kind == "video" else None,
        metadata_json={"query": query, "snippet": result.content[:2000]},
    )
    db.add(record)
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", help="课程代码")
    parser.add_argument("--year", type=int, default=2026)
    parser.add_argument("--month", type=int, default=4)
    parser.add_argument("--max-results", type=int, default=20)
    args = parser.parse_args()

    db = SessionLocal()
    PastPaperSource.__table__.create(bind=db.get_bind(), checkfirst=True)
    subject = db.query(Subject).filter(Subject.code == args.subject).first() if args.subject else None
    subject_text = f" {args.subject} {subject.name}" if subject else ""
    query = f"{args.year}年{args.month}月自考{subject_text}真题 答案 试卷 PDF 图片 视频"
    results = search_client.tavily_search_all(query, max_results=args.max_results)
    added = 0
    for result in results:
        if not result.url:
            continue
        record = save_result(db, result, subject, query)
        is_new = record.id is None
        if is_new:
            db.flush()
            added += 1
        if record.media_type != "video" and record.status == "pending":
            content, error = extract_source(result, record.media_type)
            if content:
                record.content_text = content[:50000]
                record.status = "extracted"
                if subject:
                    import_questions(db, record, subject)
            else:
                record.status = "link_only"
                record.error_message = error
    db.commit()
    print(f"saved={added} total_results={len(results)}")
    for record in db.query(PastPaperSource).order_by(PastPaperSource.id.desc()).limit(added).all():
        print(f"{record.media_type}\t{record.status}\t{record.url}")
    db.close()


if __name__ == "__main__":
    main()
