# -*- coding: utf-8 -*-
"""Question bank service."""

from datetime import datetime
import re
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.data.self_exam_catalog import normalize_course_code
from backend.elasticsearch_client import ElasticsearchClient
from backend.models.chapter import KnowledgePoint, QuestionKnowledgePoint
from backend.models.favorite import QuestionFavorite
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.online_question_provider import OnlineQuestionProvider, TEMP_ONLINE_SOURCE_PREFIX


class QuestionService:
    SCORING_RUBRIC_PATTERN = re.compile(r"\[\[SCORING_RUBRIC\]\](.*?)\[\[/SCORING_RUBRIC\]\]", re.S)

    def __init__(
        self,
        db: Session,
        es_client: Optional[ElasticsearchClient] = None,
        online_provider: Optional[OnlineQuestionProvider] = None,
    ):
        self.db = db
        self.es = es_client
        self.online_provider = online_provider or OnlineQuestionProvider()

    def search_questions(
        self,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        subject_code: Optional[str] = None,
        subject_query: Optional[str] = None,
        years: Optional[List[int]] = None,
        question_types: Optional[List[str]] = None,
        difficulty: Optional[str] = None,
        chapter_ids: Optional[List[int]] = None,
        high_frequency: Optional[bool] = None,
        online_search: bool = True,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = self.db.query(Question).filter(
            or_(Question.source.is_(None), ~Question.source.like(f"{TEMP_ONLINE_SOURCE_PREFIX}%"))
        )
        selected_subjects = self._resolve_subjects(subject_id, subject_code, subject_query)
        es_ranked_ids = self._search_question_ids_with_elasticsearch(keyword)
        search_engine = "sql"

        if keyword:
            if es_ranked_ids:
                query = query.filter(Question.id.in_(es_ranked_ids))
                search_engine = "elasticsearch"
            else:
                pattern = f"%{keyword.strip()}%"
                query = query.filter(
                    or_(
                        Question.content.ilike(pattern),
                        Question.answer.ilike(pattern),
                        Question.explanation.ilike(pattern),
                        Question.source.ilike(pattern),
                    )
                )

        if selected_subjects:
            query = query.filter(Question.subject_id.in_([subject.id for subject in selected_subjects]))
        elif subject_id or subject_code or subject_query:
            query = query.filter(Question.id == -1)

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
        if search_engine == "elasticsearch":
            questions = self._order_es_ranked_questions(query.all(), es_ranked_ids)
            questions = questions[(page - 1) * page_size : page * page_size]
        else:
            questions = (
                query.order_by(Question.frequency.desc(), Question.year.desc().nullslast(), Question.id.desc())
                .offset((page - 1) * page_size)
                .limit(page_size)
                .all()
            )
        subject_lookup = self._build_subject_lookup(questions)
        local_items = [
            self._serialize_question(question, include_answer=False, subject_lookup=subject_lookup)
            for question in questions
        ]

        online_items = self._search_online_questions(
            keyword=keyword,
            subjects=selected_subjects,
            subject_code=subject_code,
            subject_query=subject_query,
            years=years,
            enabled=online_search,
            page=page,
            page_size=page_size,
        )

        return {
            "total": total + len(online_items),
            "page": page,
            "page_size": page_size,
            "items": local_items + online_items,
            "local_count": total,
            "online_count": len(online_items),
            "online_enabled": online_search,
            "search_engine": search_engine,
        }

    def get_question_detail(self, question_id: int) -> Optional[Dict[str, Any]]:
        question = self.db.query(Question).filter(Question.id == question_id).first()
        if not question:
            return None

        data = self._serialize_question(
            question,
            include_answer=True,
            subject_lookup=self._build_subject_lookup([question]),
        )
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

    def _resolve_subjects(
        self,
        subject_id: Optional[int],
        subject_code: Optional[str],
        subject_query: Optional[str],
    ) -> List[Subject]:
        if subject_id:
            subject = self.db.query(Subject).filter(Subject.id == subject_id).first()
            return [subject] if subject else []

        if subject_code:
            normalized_code = normalize_course_code(subject_code)
            subject = self.db.query(Subject).filter(Subject.code == normalized_code).first()
            return [subject] if subject else []

        if subject_query:
            keyword = subject_query.strip()
            normalized_code = normalize_course_code(keyword)
            pattern = f"%{keyword}%"
            return (
                self.db.query(Subject)
                .filter(or_(Subject.code == normalized_code, Subject.name.ilike(pattern)))
                .order_by(Subject.code.asc(), Subject.id.asc())
                .limit(20)
                .all()
            )

        return []

    def _build_subject_lookup(self, questions: List[Question]) -> Dict[int, Subject]:
        subject_ids = sorted({question.subject_id for question in questions if question.subject_id})
        if not subject_ids:
            return {}
        subjects = self.db.query(Subject).filter(Subject.id.in_(subject_ids)).all()
        return {subject.id: subject for subject in subjects}

    def _search_question_ids_with_elasticsearch(self, keyword: Optional[str], max_results: int = 500) -> List[int]:
        keyword_text = str(keyword or "").strip()
        if not keyword_text or not self.es:
            return []
        response = self.es.search_questions(keyword_text, page=1, page_size=max_results)
        hits = response.get("hits", {}).get("hits", []) if isinstance(response, dict) else []
        ranked_ids: List[int] = []
        seen = set()
        for hit in hits:
            source = hit.get("_source") or {}
            raw_id = source.get("id") or hit.get("_id")
            try:
                question_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if question_id in seen:
                continue
            seen.add(question_id)
            ranked_ids.append(question_id)
        return ranked_ids

    @staticmethod
    def _order_es_ranked_questions(questions: List[Question], ranked_ids: List[int]) -> List[Question]:
        rank = {question_id: index for index, question_id in enumerate(ranked_ids)}
        return sorted(questions, key=lambda question: rank.get(int(question.id or 0), len(rank)))

    def _search_online_questions(
        self,
        *,
        keyword: Optional[str],
        subjects: List[Subject],
        subject_code: Optional[str],
        subject_query: Optional[str],
        years: Optional[List[int]],
        enabled: bool,
        page: int,
        page_size: int,
    ) -> List[Dict[str, Any]]:
        if not enabled or page != 1:
            return []

        selected_subject = subjects[0] if subjects else None
        normalized_code = normalize_course_code(subject_code) if subject_code else None
        query_text = (keyword or subject_query or "").strip()
        if not (query_text or selected_subject or normalized_code):
            return []

        return self.online_provider.search(
            subject_id=selected_subject.id if selected_subject else None,
            subject_code=selected_subject.code if selected_subject else normalized_code,
            subject_name=selected_subject.name if selected_subject else subject_query,
            keyword=query_text,
            year=years[0] if years else None,
            limit=max(4, min(10, page_size)),
        )

    @staticmethod
    def _serialize_question(
        question: Question,
        include_answer: bool,
        subject_lookup: Optional[Dict[int, Subject]] = None,
    ) -> Dict[str, Any]:
        subject = subject_lookup.get(question.subject_id) if subject_lookup else None
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
            "subject_code": subject.code if subject else None,
            "subject_name": subject.name if subject else None,
            "chapter_id": question.chapter_id,
            "score": question.score,
            "source": question.source,
            "is_online": False,
        }
        if include_answer:
            data.update(
                {
                    "answer": question.answer,
                    "explanation": QuestionService._strip_scoring_rubric(question.explanation),
                    "created_at": question.created_at.isoformat() if question.created_at else None,
                }
            )
        return data

    @classmethod
    def _strip_scoring_rubric(cls, explanation: Optional[str]) -> str:
        if not explanation:
            return ""
        return cls.SCORING_RUBRIC_PATTERN.sub("", explanation).strip()
