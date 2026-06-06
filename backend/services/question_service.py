# -*- coding: utf-8 -*-
"""Question bank service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.elasticsearch_client import ElasticsearchClient
from backend.models.chapter import KnowledgePoint, QuestionKnowledgePoint
from backend.models.favorite import QuestionFavorite
from backend.models.question import Question


class QuestionService:
    def __init__(self, db: Session, es_client: Optional[ElasticsearchClient] = None):
        self.db = db
        self.es = es_client

    def search_questions(
        self,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        years: Optional[List[int]] = None,
        question_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        chapter_ids: Optional[List[int]] = None,
        high_frequency: Optional[bool] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = self.db.query(Question)

        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(
                or_(
                    Question.content.ilike(pattern),
                    Question.answer.ilike(pattern),
                    Question.explanation.ilike(pattern),
                    Question.source.ilike(pattern),
                )
            )

        if subject_id:
            query = query.filter(Question.subject_id == subject_id)

        if years:
            query = query.filter(Question.year.in_(years))

        if question_types:
            query = query.filter(Question.question_type.in_(question_types))

        if difficulty:
            query = query.filter(Question.difficulty == difficulty)

        if chapter_ids:
            query = query.filter(Question.chapter_id.in_(chapter_ids))

        if high_frequency:
            query = query.filter(Question.frequency >= 3)

        total = query.count()
        questions = (
            query.order_by(Question.frequency.desc(), Question.year.desc().nullslast(), Question.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_question(question, include_answer=False) for question in questions],
        }

    def get_question_detail(self, question_id: int) -> Optional[Dict[str, Any]]:
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return None

        data = self._serialize_question(question, include_answer=True)
        data["knowledge_points"] = self._get_question_points(question.id)
        return data

    def add_to_favorites(self, user_id: int, question_id: int, tags: Optional[List[str]] = None) -> bool:
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return False

        favorite = (
            self.db.query(QuestionFavorite)
            .filter(
                and_(
                    QuestionFavorite.user_id == user_id,
                    QuestionFavorite.question_id == question_id,
                )
            )
            .first()
        )
        if favorite:
            favorite.tags = tags or favorite.tags
        else:
            favorite = QuestionFavorite(
                user_id=user_id,
                question_id=question_id,
                tags=tags or [],
                created_at=datetime.now(),
            )
            self.db.add(favorite)

        self.db.commit()
        return True

    def remove_from_favorites(self, user_id: int, question_id: int) -> bool:
        favorite = (
            self.db.query(QuestionFavorite)
            .filter(
                and_(
                    QuestionFavorite.user_id == user_id,
                    QuestionFavorite.question_id == question_id,
                )
            )
            .first()
        )
        if not favorite:
            return False

        self.db.delete(favorite)
        self.db.commit()
        return True

    def get_favorites(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        query = (
            self.db.query(Question)
            .join(QuestionFavorite, Question.id == QuestionFavorite.question_id)
            .filter(QuestionFavorite.user_id == user_id)
            .order_by(QuestionFavorite.created_at.desc())
        )
        total = query.count()
        questions = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_question(question, include_answer=False) for question in questions],
        }

    def get_high_frequency_questions(self, subject_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        questions = (
            self.db.query(Question)
            .filter(Question.subject_id == subject_id)
            .order_by(Question.frequency.desc(), Question.id.desc())
            .limit(limit)
            .all()
        )
        return [self._serialize_question(question, include_answer=False) for question in questions]

    def update_question_frequency(self, question_id: int) -> bool:
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return False
        question.frequency = (question.frequency or 0) + 1
        self.db.commit()
        return True

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
    def _serialize_question(question: Question, include_answer: bool) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": question.id,
            "content": question.content,
            "question_type": question.question_type,
            "options": question.options or [],
            "difficulty": question.difficulty,
            "year": question.year,
            "month": question.month,
            "frequency": question.frequency,
            "subject_id": question.subject_id,
            "chapter_id": question.chapter_id,
            "score": question.score,
            "source": question.source,
        }
        if include_answer:
            data.update(
                {
                    "answer": question.answer,
                    "explanation": question.explanation,
                    "created_at": question.created_at.isoformat() if question.created_at else None,
                }
            )
        return data
