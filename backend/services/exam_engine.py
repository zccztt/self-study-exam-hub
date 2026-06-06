# -*- coding: utf-8 -*-
"""Exam paper generation, session control, scoring, and wrong-book handling."""

from collections import defaultdict
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import and_
from sqlalchemy.orm import Session

from backend.models.chapter import KnowledgePoint, QuestionKnowledgePoint
from backend.models.exam import Exam, ExamMode, ExamSession, ExamStatus, WrongQuestion
from backend.models.planner import UserMastery
from backend.models.question import Question, QuestionType
from backend.redis_client import RedisClient


class ExamEngine:
    def __init__(self, db: Session, redis_client: Optional[RedisClient] = None):
        self.db = db
        self.redis = redis_client

    def generate_paper(self, subject_id: int, mode: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = config or {}
        query = self.db.query(Question).filter(Question.subject_id == subject_id)

        if mode == ExamMode.REAL_EXAM.value and config.get("year"):
            query = query.filter(Question.year == int(config["year"]))
        elif mode == ExamMode.RANDOM.value:
            if config.get("difficulty"):
                query = query.filter(Question.difficulty == config["difficulty"])
            if config.get("question_types"):
                query = query.filter(Question.question_type.in_(config["question_types"]))
        elif mode == ExamMode.CHAPTER.value and config.get("chapter_ids"):
            query = query.filter(Question.chapter_id.in_(config["chapter_ids"]))
        elif mode == ExamMode.WRONG_QUESTIONS.value and config.get("user_id"):
            wrong_query = self.db.query(WrongQuestion.question_id).filter(
                WrongQuestion.user_id == int(config["user_id"])
            )
            if not config.get("include_mastered"):
                wrong_query = wrong_query.filter(WrongQuestion.is_mastered.is_(False))
            query = query.filter(Question.id.in_(wrong_query))

        questions = query.order_by(Question.year.desc().nullslast(), Question.id.asc()).all()
        limit = int(config.get("limit", 20))
        if len(questions) > limit:
            questions = random.sample(questions, limit)

        if not questions:
            return {
                "exam_id": None,
                "subject_id": subject_id,
                "mode": mode,
                "total_score": 0,
                "duration": int(config.get("duration", 120)),
                "question_count": 0,
                "questions": [],
                "message": "No questions matched the selected criteria.",
            }

        question_ids = [question.id for question in questions]
        duration = int(config.get("duration", 120))
        exam = Exam(
            subject_id=subject_id,
            name=self._build_exam_name(mode, config),
            mode=mode,
            year=config.get("year"),
            month=config.get("month"),
            config=config,
            question_ids=question_ids,
            total_score=sum(question.score or 0 for question in questions),
            duration=duration,
        )
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)

        return {
            "exam_id": exam.id,
            "subject_id": subject_id,
            "mode": mode,
            "name": exam.name,
            "total_score": exam.total_score,
            "duration": exam.duration,
            "question_count": len(questions),
            "questions": [self._serialize_exam_question(question, include_answer=False) for question in questions],
        }

    def start_exam(self, exam_id: int, user_id: int) -> Dict[str, Any]:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise ValueError("Exam not found.")

        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=exam.duration)
        session = ExamSession(
            session_id=session_id,
            exam_id=exam_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            status=ExamStatus.IN_PROGRESS.value,
            answers={},
        )
        self.db.add(session)
        self.db.commit()

        if self.redis:
            self.redis.set(
                f"exam_session:{session_id}",
                {
                    "user_id": user_id,
                    "exam_id": exam_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
                expire=exam.duration * 60,
            )

        return {
            "session_id": session_id,
            "exam_id": exam_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": exam.duration,
            "status": session.status,
        }

    def submit_answer(self, session_id: str, question_id: int, answer: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "message": "Exam session not found."}

        if session.status != ExamStatus.IN_PROGRESS.value:
            return {"success": False, "message": "Exam session is not active."}

        if session.end_time and datetime.now() > session.end_time:
            session.status = ExamStatus.TIMEOUT.value
            self.db.commit()
            return {"success": False, "message": "Exam session has timed out."}

        answers = dict(session.answers or {})
        answers[str(question_id)] = answer
        session.answers = answers
        self.db.commit()

        return {"success": True, "message": "Answer saved.", "answered_count": len(answers)}

    def submit_paper(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")

        score_result = self.auto_score(session_id)
        session.status = ExamStatus.COMPLETED.value
        session.score = score_result["score"]
        session.correct_count = score_result["correct_count"]
        session.total_count = score_result["total_count"]
        session.submitted_at = datetime.now()
        self.db.commit()

        self.archive_wrong_questions(session_id, session.user_id, score_result)
        self.update_user_mastery(session.user_id, score_result)
        if self.redis:
            self.redis.delete(f"exam_session:{session_id}")
        return score_result

    def auto_score(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")

        exam = self.db.query(Exam).filter(Exam.id == session.exam_id).first()
        if not exam:
            raise ValueError("Exam not found.")

        question_ids = [int(question_id) for question_id in (exam.question_ids or [])]
        questions = self.db.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_by_id = {question.id: question for question in questions}

        score = 0
        correct_count = 0
        objective_count = 0
        wrong_questions: List[int] = []
        question_analysis: List[Dict[str, Any]] = []

        for question_id in question_ids:
            question = questions_by_id.get(question_id)
            if not question:
                continue

            user_answer = (session.answers or {}).get(str(question.id), "")
            objective = question.question_type in {
                QuestionType.SINGLE_CHOICE.value,
                QuestionType.MULTIPLE_CHOICE.value,
                QuestionType.FILL_BLANK.value,
            }
            if objective:
                objective_count += 1
                is_correct = self._check_answer(question, user_answer)
                earned_score = question.score if is_correct else 0
                score += earned_score
                correct_count += 1 if is_correct else 0
                if not is_correct:
                    wrong_questions.append(question.id)
            else:
                is_correct = None
                earned_score = None

            question_analysis.append(
                {
                    "question_id": question.id,
                    "content": question.content,
                    "user_answer": user_answer,
                    "correct_answer": question.answer,
                    "is_correct": is_correct,
                    "score": earned_score,
                    "full_score": question.score,
                    "explanation": question.explanation,
                }
            )

        total_count = len(question_ids)
        return {
            "session_id": session_id,
            "score": score,
            "total_score": exam.total_score,
            "correct_count": correct_count,
            "total_count": total_count,
            "objective_count": objective_count,
            "manual_count": total_count - objective_count,
            "accuracy": correct_count / objective_count if objective_count else 0,
            "wrong_questions": wrong_questions,
            "question_analysis": question_analysis,
        }

    def archive_wrong_questions(
        self,
        session_id: str,
        user_id: int,
        score_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        score_result = score_result or self.auto_score(session_id)
        analysis = score_result.get("question_analysis", [])
        answers_by_id = {item["question_id"]: item.get("user_answer", "") for item in analysis}
        wrong_ids = set(score_result.get("wrong_questions", []))
        answered_ids = [item["question_id"] for item in analysis if item.get("is_correct") is not None]
        existing_rows = (
            self.db.query(WrongQuestion)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id.in_(answered_ids))
            .all()
            if answered_ids
            else []
        )
        existing_by_question = {row.question_id: row for row in existing_rows}

        for question_id in wrong_ids:
            existing = (
                existing_by_question.get(question_id)
                or self.db.query(WrongQuestion)
                .filter(and_(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id))
                .first()
            )
            if existing:
                existing.wrong_count = (existing.wrong_count or 0) + 1
                existing.user_answer = answers_by_id.get(question_id)
                existing.last_wrong_at = datetime.now()
                existing.is_mastered = False
            else:
                self.db.add(
                    WrongQuestion(
                        user_id=user_id,
                        question_id=question_id,
                        session_id=session_id,
                        user_answer=answers_by_id.get(question_id),
                        wrong_count=1,
                        last_wrong_at=datetime.now(),
                    )
                )

        for item in analysis:
            question_id = item["question_id"]
            if item.get("is_correct") is True and question_id in existing_by_question:
                existing_by_question[question_id].is_mastered = True
                existing_by_question[question_id].user_answer = answers_by_id.get(question_id)

        self.db.commit()
        return True

    def update_user_mastery(self, user_id: int, score_result: Dict[str, Any]) -> bool:
        analysis = [
            item
            for item in score_result.get("question_analysis", [])
            if item.get("is_correct") is not None
        ]
        if not analysis:
            return False

        question_ids = [item["question_id"] for item in analysis]
        links = (
            self.db.query(QuestionKnowledgePoint)
            .filter(QuestionKnowledgePoint.question_id.in_(question_ids))
            .all()
        )
        point_ids_by_question: Dict[int, List[int]] = defaultdict(list)
        for link in links:
            point_ids_by_question[link.question_id].append(link.knowledge_point_id)

        now = datetime.now()
        changed = False
        for item in analysis:
            point_ids = point_ids_by_question.get(item["question_id"], [])
            if not point_ids:
                continue

            for point_id in point_ids:
                mastery = (
                    self.db.query(UserMastery)
                    .filter(UserMastery.user_id == user_id, UserMastery.knowledge_point_id == point_id)
                    .first()
                )
                if not mastery:
                    mastery = UserMastery(
                        user_id=user_id,
                        knowledge_point_id=point_id,
                        mastery_level=0.0,
                        correct_count=0,
                        wrong_count=0,
                    )
                    self.db.add(mastery)

                if item["is_correct"]:
                    mastery.correct_count = (mastery.correct_count or 0) + 1
                else:
                    mastery.wrong_count = (mastery.wrong_count or 0) + 1

                attempts = max((mastery.correct_count or 0) + (mastery.wrong_count or 0), 1)
                mastery.mastery_level = round((mastery.correct_count or 0) / attempts, 2)
                mastery.last_practice_time = now
                mastery.next_review_time = self._next_review_time(now, mastery.mastery_level, bool(item["is_correct"]))
                changed = True

        if changed:
            self.db.commit()
        return changed

    def get_exam_history(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        query = (
            self.db.query(ExamSession)
            .filter(ExamSession.user_id == user_id)
            .order_by(ExamSession.start_time.desc())
        )
        total = query.count()
        sessions = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_session(session) for session in sessions],
        }

    def get_wrong_questions(
        self,
        user_id: int,
        subject_id: Optional[int] = None,
        chapter_ids: Optional[List[int]] = None,
        is_mastered: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = (
            self.db.query(WrongQuestion, Question)
            .join(Question, WrongQuestion.question_id == Question.id)
            .filter(WrongQuestion.user_id == user_id)
        )
        if subject_id:
            query = query.filter(Question.subject_id == subject_id)
        if chapter_ids:
            query = query.filter(Question.chapter_id.in_(chapter_ids))
        if is_mastered is not None:
            query = query.filter(WrongQuestion.is_mastered.is_(is_mastered))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(Question.content.ilike(pattern))

        total = query.count()
        rows = (
            query.order_by(WrongQuestion.is_mastered.asc(), WrongQuestion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_wrong_question(wrong, question) for wrong, question in rows],
        }

    def update_wrong_question(
        self,
        user_id: int,
        question_id: int,
        is_mastered: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        row = (
            self.db.query(WrongQuestion, Question)
            .join(Question, WrongQuestion.question_id == Question.id)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id)
            .first()
        )
        if not row:
            return None

        wrong, question = row
        if is_mastered is not None:
            wrong.is_mastered = is_mastered
        if tags is not None:
            wrong.tags = tags
        if note is not None:
            wrong.note = note
        self.db.commit()
        self.db.refresh(wrong)
        return self._serialize_wrong_question(wrong, question)

    def remove_wrong_question(self, user_id: int, question_id: int) -> bool:
        wrong = (
            self.db.query(WrongQuestion)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id)
            .first()
        )
        if not wrong:
            return False
        self.db.delete(wrong)
        self.db.commit()
        return True

    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")
        return self._serialize_session(session)

    @staticmethod
    def _build_exam_name(mode: str, config: Dict[str, Any]) -> str:
        labels = {
            ExamMode.REAL_EXAM.value: "Past paper",
            ExamMode.RANDOM.value: "Random paper",
            ExamMode.CHAPTER.value: "Chapter practice",
            ExamMode.WRONG_QUESTIONS.value: "Wrong question retry",
        }
        suffix = f" {config['year']}" if config.get("year") else ""
        return f"{labels.get(mode, 'Exam')}{suffix}"

    @staticmethod
    def _serialize_exam_question(question: Question, include_answer: bool) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": question.id,
            "content": question.content,
            "question_type": question.question_type,
            "options": question.options or [],
            "score": question.score,
            "difficulty": question.difficulty,
            "year": question.year,
            "month": question.month,
        }
        if include_answer:
            data["answer"] = question.answer
            data["explanation"] = question.explanation
        return data

    def _serialize_wrong_question(self, wrong: WrongQuestion, question: Question) -> Dict[str, Any]:
        return {
            "id": wrong.id,
            "user_id": wrong.user_id,
            "question_id": wrong.question_id,
            "session_id": wrong.session_id,
            "user_answer": wrong.user_answer,
            "wrong_count": wrong.wrong_count,
            "is_mastered": wrong.is_mastered,
            "tags": wrong.tags or [],
            "note": wrong.note,
            "last_wrong_at": wrong.last_wrong_at.isoformat() if wrong.last_wrong_at else None,
            "created_at": wrong.created_at.isoformat() if wrong.created_at else None,
            "question": self._serialize_exam_question(question, include_answer=True),
            "knowledge_points": self._get_question_points(question.id),
        }

    def _get_question_points(self, question_id: int) -> List[Dict[str, Any]]:
        points = (
            self.db.query(KnowledgePoint)
            .join(QuestionKnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
            .filter(QuestionKnowledgePoint.question_id == question_id)
            .all()
        )
        return [
            {
                "id": point.id,
                "name": point.name,
                "chapter_id": point.chapter_id,
                "importance": point.importance,
                "frequency": point.frequency,
            }
            for point in points
        ]

    @staticmethod
    def _check_answer(question: Question, user_answer: str) -> bool:
        correct_answer = (question.answer or "").strip().upper()
        normalized_user_answer = (user_answer or "").strip().upper()
        if question.question_type == QuestionType.MULTIPLE_CHOICE.value:
            correct_letters = set(re.sub(r"[^A-Z]", "", correct_answer))
            user_letters = set(re.sub(r"[^A-Z]", "", normalized_user_answer))
            return bool(correct_letters) and correct_letters == user_letters
        if question.question_type == QuestionType.FILL_BLANK.value:
            alternatives = [
                ExamEngine._normalize_text_answer(item)
                for item in re.split(r"[|/;；、]", question.answer or "")
                if item.strip()
            ]
            user_value = ExamEngine._normalize_text_answer(user_answer)
            return user_value in alternatives if alternatives else user_value == ExamEngine._normalize_text_answer(correct_answer)
        return ExamEngine._normalize_text_answer(correct_answer) == ExamEngine._normalize_text_answer(normalized_user_answer)

    @staticmethod
    def _normalize_text_answer(value: str) -> str:
        return re.sub(r"\s+", "", str(value or "").strip().upper())

    @staticmethod
    def _next_review_time(base_time: datetime, mastery_level: float, was_correct: bool) -> datetime:
        if not was_correct:
            return base_time + timedelta(days=1)
        if mastery_level >= 0.85:
            return base_time + timedelta(days=14)
        if mastery_level >= 0.65:
            return base_time + timedelta(days=7)
        return base_time + timedelta(days=3)

    def _get_session(self, session_id: str) -> Optional[ExamSession]:
        return self.db.query(ExamSession).filter(ExamSession.session_id == session_id).first()

    @staticmethod
    def _serialize_session(session: ExamSession) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "exam_id": session.exam_id,
            "user_id": session.user_id,
            "status": session.status,
            "answers": session.answers or {},
            "score": session.score,
            "correct_count": session.correct_count,
            "total_count": session.total_count,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
        }
