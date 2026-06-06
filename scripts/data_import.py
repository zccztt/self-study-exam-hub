#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Import questions, videos, and knowledge-point data into the database."""

import argparse
import csv
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import and_  # noqa: E402

from backend.database import SessionLocal  # noqa: E402
from backend.elasticsearch_client import QUESTION_INDEX, es_client  # noqa: E402
from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint  # noqa: E402
from backend.models.question import Difficulty, Question, QuestionType  # noqa: E402
from backend.models.subject import Subject  # noqa: E402
from backend.models.video import Video, VideoKnowledgePoint, VideoQuestion, VideoSource  # noqa: E402


def load_data(source_path: Path) -> Any:
    if source_path.is_dir():
        records: List[Any] = []
        for item in sorted(source_path.rglob("*")):
            if item.suffix.lower() not in {".json", ".csv"}:
                continue
            data = load_data(item)
            if isinstance(data, list):
                records.extend(data)
            else:
                records.append(data)
        return records

    suffix = source_path.suffix.lower()
    if suffix == ".json":
        with source_path.open("r", encoding="utf-8-sig") as file:
            return json.load(file)
    if suffix == ".csv":
        with source_path.open("r", encoding="utf-8-sig", newline="") as file:
            return list(csv.DictReader(file))
    raise ValueError(f"Unsupported file format: {suffix}")


def to_int(value: Any, default: Optional[int] = None) -> Optional[int]:
    if value is None or value == "":
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def to_list(value: Any) -> List[Any]:
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        if stripped.startswith("["):
            try:
                parsed = json.loads(stripped)
                return parsed if isinstance(parsed, list) else [parsed]
            except json.JSONDecodeError:
                pass
        separator = "|" if "|" in stripped else ","
        return [item.strip() for item in stripped.split(separator) if item.strip()]
    return [value]


def parse_options(value: Any) -> List[str]:
    return [str(item).strip() for item in to_list(value)]


def parse_datetime(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None


def stable_auto_code(name: str) -> str:
    digest = hashlib.md5(name.encode("utf-8")).hexdigest()[:8]
    return f"AUTO-{digest}"


def normalize_enum(value: Any, allowed: List[str], default: str) -> str:
    text = str(value or "").strip()
    return text if text in allowed else default


def ensure_subject(db, subject_id: Optional[int], name: Optional[str], code: Optional[str] = None) -> Subject:
    if subject_id:
        subject = db.query(Subject).filter(Subject.id == subject_id).first()
        if subject:
            return subject

    if code:
        subject = db.query(Subject).filter(Subject.code == code).first()
        if subject:
            return subject

    if name:
        subject = db.query(Subject).filter(Subject.name == name).first()
        if subject:
            return subject

    subject_name = name or f"未命名科目{subject_id or ''}".strip()
    subject = Subject(
        **({"id": subject_id} if subject_id else {}),
        code=code or stable_auto_code(subject_name),
        name=subject_name,
        category="public",
        exam_duration=150,
        total_score=100,
    )
    db.add(subject)
    db.flush()
    return subject


def ensure_chapter(
    db,
    subject_id: int,
    chapter_id: Optional[int],
    name: Optional[str],
    order: int = 0,
    parent_id: Optional[int] = None,
) -> Chapter:
    if chapter_id:
        chapter = db.query(Chapter).filter(Chapter.id == chapter_id).first()
        if chapter:
            return chapter

    chapter_name = name or "未分章"
    chapter = (
        db.query(Chapter)
        .filter(
            Chapter.subject_id == subject_id,
            Chapter.name == chapter_name,
            Chapter.parent_id == parent_id,
        )
        .first()
    )
    if chapter:
        return chapter

    chapter = Chapter(
        **({"id": chapter_id} if chapter_id else {}),
        subject_id=subject_id,
        name=chapter_name,
        order=order,
        parent_id=parent_id,
    )
    db.add(chapter)
    db.flush()
    return chapter


def ensure_knowledge_point(
    db,
    chapter_id: int,
    name: str,
    description: Optional[str] = None,
    importance: str = "medium",
    frequency: int = 0,
    point_id: Optional[int] = None,
) -> KnowledgePoint:
    if point_id:
        point = db.query(KnowledgePoint).filter(KnowledgePoint.id == point_id).first()
        if point:
            return point

    point = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.chapter_id == chapter_id, KnowledgePoint.name == name)
        .first()
    )
    if point:
        point.description = description or point.description
        point.importance = importance or point.importance
        point.frequency = max(point.frequency or 0, frequency or 0)
        return point

    point = KnowledgePoint(
        **({"id": point_id} if point_id else {}),
        chapter_id=chapter_id,
        name=name,
        description=description,
        importance=importance or "medium",
        frequency=frequency or 0,
    )
    db.add(point)
    db.flush()
    return point


def link_question_point(db, question_id: int, point_id: int) -> None:
    exists = (
        db.query(QuestionKnowledgePoint)
        .filter(
            QuestionKnowledgePoint.question_id == question_id,
            QuestionKnowledgePoint.knowledge_point_id == point_id,
        )
        .first()
    )
    if not exists:
        db.add(QuestionKnowledgePoint(question_id=question_id, knowledge_point_id=point_id))


def link_video_point(db, video_id: int, point_id: int) -> None:
    exists = (
        db.query(VideoKnowledgePoint)
        .filter(VideoKnowledgePoint.video_id == video_id, VideoKnowledgePoint.knowledge_point_id == point_id)
        .first()
    )
    if not exists:
        db.add(VideoKnowledgePoint(video_id=video_id, knowledge_point_id=point_id))


def link_video_question(db, video_id: int, question_id: int) -> None:
    exists = (
        db.query(VideoQuestion)
        .filter(VideoQuestion.video_id == video_id, VideoQuestion.question_id == question_id)
        .first()
    )
    if not exists:
        db.add(VideoQuestion(video_id=video_id, question_id=question_id))


def serialize_question_for_search(question: Question) -> Dict[str, Any]:
    return {
        "id": question.id,
        "subject_id": question.subject_id,
        "content": question.content,
        "answer": question.answer,
        "explanation": question.explanation,
        "question_type": question.question_type,
        "year": question.year,
        "difficulty": question.difficulty,
        "frequency": question.frequency,
    }


def import_questions(source_path: str) -> bool:
    records = load_data(Path(source_path))
    if not isinstance(records, list):
        raise ValueError("Question data must be a JSON array or CSV table.")

    db = SessionLocal()
    indexed_documents: List[Dict[str, Any]] = []
    imported = 0
    try:
        for row in records:
            if not isinstance(row, dict):
                continue
            content = str(row.get("content") or "").strip()
            if not content:
                print("跳过缺少 content 的题目记录")
                continue

            subject = ensure_subject(
                db,
                to_int(row.get("subject_id")),
                row.get("subject_name") or row.get("subject"),
                row.get("subject_code"),
            )
            chapter = ensure_chapter(
                db,
                subject.id,
                to_int(row.get("chapter_id")),
                row.get("chapter_name") or row.get("chapter"),
                to_int(row.get("chapter_order"), 0) or 0,
            )
            question_id = to_int(row.get("id"))
            question = db.query(Question).filter(Question.id == question_id).first() if question_id else None
            if not question:
                question = Question(**({"id": question_id} if question_id else {}))
                db.add(question)

            question.subject_id = subject.id
            question.chapter_id = chapter.id
            question.content = content
            question.question_type = normalize_enum(
                row.get("question_type") or row.get("type"),
                [item.value for item in QuestionType],
                QuestionType.SINGLE_CHOICE.value if parse_options(row.get("options")) else QuestionType.SHORT_ANSWER.value,
            )
            question.options = parse_options(row.get("options"))
            question.answer = str(row.get("answer") or "")
            question.explanation = row.get("explanation")
            question.year = to_int(row.get("year"))
            question.month = to_int(row.get("month"))
            question.difficulty = normalize_enum(
                row.get("difficulty"),
                [item.value for item in Difficulty],
                Difficulty.MEDIUM.value,
            )
            question.frequency = to_int(row.get("frequency"), 1) or 1
            question.score = to_int(row.get("score"), 2) or 2
            question.source = row.get("source")
            db.flush()

            for point_name in to_list(row.get("knowledge_points")):
                point = ensure_knowledge_point(
                    db,
                    chapter.id,
                    str(point_name),
                    importance="medium",
                    frequency=question.frequency,
                )
                link_question_point(db, question.id, point.id)

            indexed_documents.append(serialize_question_for_search(question))
            imported += 1

        db.commit()
        es_client.bulk_index(QUESTION_INDEX, indexed_documents)
        print(f"题库数据导入完成：{imported} 条")
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def import_videos(source_path: str) -> bool:
    records = load_data(Path(source_path))
    if not isinstance(records, list):
        raise ValueError("Video data must be a JSON array or CSV table.")

    db = SessionLocal()
    imported = 0
    try:
        for row in records:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title") or "").strip()
            url = str(row.get("url") or "").strip()
            if not title or not url:
                print("跳过缺少 title/url 的视频记录")
                continue

            subject = ensure_subject(
                db,
                to_int(row.get("subject_id")),
                row.get("subject_name") or row.get("subject"),
                row.get("subject_code"),
            )
            chapter = ensure_chapter(
                db,
                subject.id,
                to_int(row.get("chapter_id")),
                row.get("chapter_name") or row.get("chapter"),
                to_int(row.get("chapter_order"), 0) or 0,
            )
            video_id = to_int(row.get("id"))
            video = db.query(Video).filter(Video.id == video_id).first() if video_id else None
            if not video:
                video = Video(**({"id": video_id} if video_id else {}))
                db.add(video)

            video.title = title
            video.url = url
            video.source = normalize_enum(
                row.get("source"),
                [item.value for item in VideoSource],
                VideoSource.CUSTOM.value,
            )
            video.duration = to_int(row.get("duration"))
            video.author = row.get("author")
            video.view_count = to_int(row.get("view_count"), 0) or 0
            video.publish_date = parse_datetime(row.get("publish_date"))
            video.subject_id = subject.id
            video.chapter_id = chapter.id
            video.thumbnail = row.get("thumbnail")
            video.description = row.get("description")
            video.tags = [str(item) for item in to_list(row.get("tags"))]
            video.is_active = 1
            db.flush()

            for point_name in to_list(row.get("knowledge_points")):
                point = ensure_knowledge_point(db, chapter.id, str(point_name), importance="medium")
                link_video_point(db, video.id, point.id)

            for question_id in to_list(row.get("related_question_ids")):
                parsed_question_id = to_int(question_id)
                if parsed_question_id and db.query(Question).filter(Question.id == parsed_question_id).first():
                    link_video_question(db, video.id, parsed_question_id)

            imported += 1

        db.commit()
        print(f"视频数据导入完成：{imported} 条")
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def import_knowledge(source_path: str) -> bool:
    data = load_data(Path(source_path))
    subjects = data if isinstance(data, list) else [data]
    if not all(isinstance(item, dict) for item in subjects):
        raise ValueError("Knowledge data must be a JSON object or array.")

    db = SessionLocal()
    imported_points = 0
    try:
        for subject_data in subjects:
            subject = ensure_subject(
                db,
                to_int(subject_data.get("subject_id") or subject_data.get("id")),
                subject_data.get("subject_name") or subject_data.get("name"),
                subject_data.get("subject_code") or subject_data.get("code"),
            )
            chapters = subject_data.get("chapters") or []
            for chapter_index, chapter_data in enumerate(chapters, start=1):
                chapter = ensure_chapter(
                    db,
                    subject.id,
                    to_int(chapter_data.get("id")),
                    chapter_data.get("name"),
                    to_int(chapter_data.get("order"), chapter_index) or chapter_index,
                )

                for point_data in chapter_data.get("knowledge_points") or []:
                    if isinstance(point_data, str):
                        ensure_knowledge_point(db, chapter.id, point_data)
                        imported_points += 1
                    elif isinstance(point_data, dict) and point_data.get("name"):
                        ensure_knowledge_point(
                            db,
                            chapter.id,
                            point_data["name"],
                            point_data.get("description"),
                            point_data.get("importance", "medium"),
                            to_int(point_data.get("frequency"), 0) or 0,
                            to_int(point_data.get("id")),
                        )
                        imported_points += 1

                for section_index, section_data in enumerate(chapter_data.get("sections") or [], start=1):
                    section = ensure_chapter(
                        db,
                        subject.id,
                        to_int(section_data.get("id")),
                        section_data.get("name"),
                        to_int(section_data.get("order"), section_index) or section_index,
                        parent_id=chapter.id,
                    )
                    for point_data in section_data.get("knowledge_points") or []:
                        if isinstance(point_data, str):
                            ensure_knowledge_point(db, section.id, point_data)
                            imported_points += 1
                        elif isinstance(point_data, dict) and point_data.get("name"):
                            ensure_knowledge_point(
                                db,
                                section.id,
                                point_data["name"],
                                point_data.get("description"),
                                point_data.get("importance", "medium"),
                                to_int(point_data.get("frequency"), 0) or 0,
                                to_int(point_data.get("id")),
                            )
                            imported_points += 1

        db.commit()
        print(f"知识点数据导入完成：{imported_points} 个知识点")
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="自考真题系统数据导入工具")
    parser.add_argument("--type", required=True, choices=["questions", "videos", "knowledge"], help="数据类型")
    parser.add_argument("--source", required=True, help="数据源路径")

    args = parser.parse_args()
    source_path = Path(args.source)
    if not source_path.exists():
        print(f"错误: 数据源路径不存在: {args.source}", file=sys.stderr)
        sys.exit(1)

    try:
        if args.type == "questions":
            success = import_questions(str(source_path))
        elif args.type == "videos":
            success = import_videos(str(source_path))
        else:
            success = import_knowledge(str(source_path))

        if success:
            print(f"\n{args.type} 数据导入成功")
            sys.exit(0)
        print(f"\n{args.type} 数据导入失败", file=sys.stderr)
        sys.exit(1)
    except Exception as exc:
        print(f"\n导入过程中发生错误: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
