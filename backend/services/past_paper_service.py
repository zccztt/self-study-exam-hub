# -*- coding: utf-8 -*-
"""Past paper service: list, detail, and start exam from historical papers."""

import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.enrollment import Province
from backend.models.exam import Exam, ExamMode, ExamSession, ExamStatus
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject


class PastPaperService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # List past papers with filters
    # ------------------------------------------------------------------
    def list_papers(
        self,
        subject_id: Optional[int] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        province_id: Optional[int] = None,
        paper_type: Optional[str] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = self.db.query(PastPaper).filter(PastPaper.is_published.is_(True))
        if subject_id:
            query = query.filter(PastPaper.subject_id == subject_id)
        if year:
            query = query.filter(PastPaper.year == year)
        if month:
            query = query.filter(PastPaper.month == month)
        if province_id:
            query = query.filter(PastPaper.province_id == province_id)

        # Filter by paper type: real vs mock
        if paper_type == "real":
            query = query.filter(PastPaper.source.like("%真实真题%"))
        elif paper_type == "mock":
            query = query.filter(~PastPaper.source.like("%真实真题%"))

        # Keyword search: match subject code or name
        if keyword and keyword.strip():
            kw = keyword.strip()
            matching_subject_ids = (
                self.db.query(Subject.id)
                .filter(
                    (Subject.code.like(f"%{kw}%")) | (Subject.name.like(f"%{kw}%"))
                )
                .all()
            )
            matched_ids = [r[0] for r in matching_subject_ids]
            if matched_ids:
                query = query.filter(PastPaper.subject_id.in_(matched_ids))
            else:
                # No match, also try paper name directly
                query = query.filter(PastPaper.name.like(f"%{kw}%"))

        total = query.count()
        items = (
            query.order_by(PastPaper.year.desc(), PastPaper.month.desc(), PastPaper.subject_id)
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        # Batch load subject names
        subject_ids = list({p.subject_id for p in items})
        subjects = (
            self.db.query(Subject.id, Subject.name)
            .filter(Subject.id.in_(subject_ids))
            .all()
            if subject_ids
            else []
        )
        subject_map = {s.id: s.name for s in subjects}

        # Batch load province names
        province_ids = list({p.province_id for p in items if p.province_id})
        provinces = (
            self.db.query(Province.id, Province.name)
            .filter(Province.id.in_(province_ids))
            .all()
            if province_ids
            else []
        )
        province_map = {p.id: p.name for p in provinces}

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [
                self._serialize_paper(p, subject_map, province_map)
                for p in items
            ],
        }

    # ------------------------------------------------------------------
    # Get paper detail with full questions
    # ------------------------------------------------------------------
    def get_paper_detail(self, paper_id: int) -> Optional[Dict[str, Any]]:
        paper = self.db.query(PastPaper).filter(
            PastPaper.id == paper_id,
            PastPaper.is_published.is_(True),
        ).first()
        if not paper:
            return None

        subject = self.db.query(Subject).filter(Subject.id == paper.subject_id).first()
        province = None
        if paper.province_id:
            province = self.db.query(Province).filter(Province.id == paper.province_id).first()

        # Load questions in order
        question_ids = paper.question_ids or []
        questions_map = {}
        if question_ids:
            questions = self.db.query(Question).filter(Question.id.in_(question_ids)).all()
            questions_map = {q.id: q for q in questions}

        ordered_questions = [questions_map[qid] for qid in question_ids if qid in questions_map]

        return {
            "id": paper.id,
            "subject_id": paper.subject_id,
            "subject_name": subject.name if subject else "",
            "name": paper.name,
            "year": paper.year,
            "month": paper.month,
            "province_name": province.name if province else None,
            "total_score": paper.total_score,
            "duration": paper.duration,
            "question_count": len(ordered_questions),
            "paper_config": paper.paper_config,
            "source": paper.source,
            "questions": [
                self._serialize_question(q, include_answer=False)
                for q in ordered_questions
            ],
        }

    # ------------------------------------------------------------------
    # Start a past paper (creates Exam + ExamSession)
    # ------------------------------------------------------------------
    def start_paper(self, paper_id: int, user_id: int) -> Dict[str, Any]:
        paper = self.db.query(PastPaper).filter(
            PastPaper.id == paper_id,
            PastPaper.is_published.is_(True),
        ).first()
        if not paper:
            raise ValueError("真题试卷不存在")

        question_ids = paper.question_ids or []
        if not question_ids:
            raise ValueError("该真题试卷暂无题目")

        # Check for existing in-progress session for this paper+user
        existing_session = (
            self.db.query(ExamSession)
            .join(Exam, Exam.id == ExamSession.exam_id)
            .filter(
                ExamSession.user_id == user_id,
                ExamSession.status == ExamStatus.IN_PROGRESS.value,
                Exam.config["past_paper_id"].as_integer() == paper_id,
            )
            .first()
        )
        if existing_session:
            return {
                "session_id": existing_session.session_id,
                "exam_id": existing_session.exam_id,
                "start_time": existing_session.start_time.isoformat() if existing_session.start_time else None,
                "end_time": existing_session.end_time.isoformat() if existing_session.end_time else None,
                "duration": paper.duration,
                "status": existing_session.status,
            }

        # Create an Exam record for this attempt
        try:
            exam = Exam(
                subject_id=paper.subject_id,
                name=paper.name,
                mode=ExamMode.REAL_EXAM.value,
                year=paper.year,
                month=paper.month,
                config={"past_paper_id": paper.id},
                question_ids=question_ids,
                total_score=paper.total_score,
                duration=paper.duration,
            )
            self.db.add(exam)
            self.db.flush()

            # Create ExamSession
            session_id = str(uuid.uuid4())
            now = datetime.now()
            end_time = now + timedelta(minutes=paper.duration)

            session = ExamSession(
                session_id=session_id,
                user_id=user_id,
                exam_id=exam.id,
                status=ExamStatus.IN_PROGRESS.value,
                answers={},
                start_time=now,
                end_time=end_time,
            )
            self.db.add(session)
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        return {
            "session_id": session_id,
            "exam_id": exam.id,
            "start_time": now.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": paper.duration,
            "status": ExamStatus.IN_PROGRESS.value,
        }

    # ------------------------------------------------------------------
    # Available subjects that have past papers
    # ------------------------------------------------------------------
    def get_available_subjects(self, paper_type: Optional[str] = None) -> List[Dict[str, Any]]:
        query = (
            self.db.query(
                PastPaper.subject_id,
                Subject.code,
                Subject.name,
                func.count(PastPaper.id).label("paper_count"),
            )
            .join(Subject, Subject.id == PastPaper.subject_id)
            .filter(PastPaper.is_published.is_(True))
        )
        if paper_type == "real":
            query = query.filter(PastPaper.source.like("%真实真题%"))
        elif paper_type == "mock":
            query = query.filter(~PastPaper.source.like("%真实真题%"))
        rows = (
            query.group_by(PastPaper.subject_id, Subject.code, Subject.name)
            .order_by(func.count(PastPaper.id).desc())
            .all()
        )
        return [
            {
                "subject_id": r[0],
                "code": r[1],
                "name": r[2],
                "paper_count": r[3],
            }
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Available years for a subject
    # ------------------------------------------------------------------
    def get_available_years(self, subject_id: Optional[int] = None, paper_type: Optional[str] = None) -> List[int]:
        query = self.db.query(PastPaper.year).filter(PastPaper.is_published.is_(True))
        if subject_id:
            query = query.filter(PastPaper.subject_id == subject_id)
        if paper_type == "real":
            query = query.filter(PastPaper.source.like("%真实真题%"))
        elif paper_type == "mock":
            query = query.filter(~PastPaper.source.like("%真实真题%"))
        rows = query.distinct().order_by(PastPaper.year.desc()).all()
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Serialization helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _serialize_paper(
        paper: PastPaper,
        subject_map: Dict[int, str],
        province_map: Dict[int, str],
    ) -> Dict[str, Any]:
        question_ids = paper.question_ids or []
        is_real = "真实真题" in (paper.source or "")
        return {
            "id": paper.id,
            "subject_id": paper.subject_id,
            "subject_name": subject_map.get(paper.subject_id, ""),
            "name": paper.name,
            "year": paper.year,
            "month": paper.month,
            "province_name": province_map.get(paper.province_id, None) if paper.province_id else None,
            "total_score": paper.total_score,
            "duration": paper.duration,
            "question_count": len(question_ids),
            "source": paper.source,
            "paper_type": "real" if is_real else "mock",
        }

    @staticmethod
    def _serialize_question(question: Question, include_answer: bool) -> Dict[str, Any]:
        data = {
            "id": question.id,
            "content": question.content,
            "question_type": question.question_type,
            "options": question.options or [],
            "score": question.score,
            "difficulty": question.difficulty,
            "year": question.year,
            "month": question.month,
            "chapter_id": question.chapter_id,
        }
        if include_answer:
            data["answer"] = question.answer
            data["explanation"] = question.explanation
        return data
