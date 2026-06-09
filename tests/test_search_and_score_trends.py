# -*- coding: utf-8 -*-
"""Tests for search integration and score trend analytics."""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.models.chapter import Chapter
from backend.models.exam import Exam, ExamSession, ExamStatus, WrongQuestion
from backend.models.question import Difficulty, Question, QuestionType
from backend.models.subject import Subject
from backend.services.analysis_service import AnalysisService
from backend.services.question_service import QuestionService


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def _seed_subject(db):
    db.add(Subject(id=1, code="03709", name="马克思主义基本原理概论"))
    db.add(Chapter(id=1, subject_id=1, name="第一章", order=1))
    db.add(Chapter(id=2, subject_id=1, name="第二章", order=2))
    db.commit()


def _add_question(db, question_id: int, content: str, chapter_id: int) -> None:
    db.add(
        Question(
            id=question_id,
            subject_id=1,
            chapter_id=chapter_id,
            content=content,
            question_type=QuestionType.SINGLE_CHOICE.value,
            difficulty=Difficulty.MEDIUM.value,
            answer="A",
            frequency=1,
            score=2,
            year=2026,
        )
    )


class FakeElasticsearch:
    def search_questions(self, keyword: str, page: int = 1, page_size: int = 20):
        assert keyword == "实践"
        return {
            "hits": {
                "hits": [
                    {"_id": "2", "_source": {"id": 2}},
                    {"_id": "1", "_source": {"id": 1}},
                ]
            }
        }


def test_question_search_uses_elasticsearch_ranked_ids() -> None:
    db = _session()
    try:
        _seed_subject(db)
        _add_question(db, 1, "实践是认识的来源", 1)
        _add_question(db, 2, "实践是检验真理的标准", 1)
        _add_question(db, 3, "完全不相关", 2)
        db.commit()

        result = QuestionService(db, es_client=FakeElasticsearch()).search_questions(
            keyword="实践",
            online_search=False,
        )

        assert result["search_engine"] == "elasticsearch"
        assert [item["id"] for item in result["items"]] == [2, 1]
        assert result["local_count"] == 2
    finally:
        db.close()


def test_score_trends_include_subject_and_chapter_accuracy() -> None:
    db = _session()
    try:
        _seed_subject(db)
        _add_question(db, 1, "题目1", 1)
        _add_question(db, 2, "题目2", 1)
        _add_question(db, 3, "题目3", 2)
        exam = Exam(
            id=1,
            subject_id=1,
            name="模拟卷",
            mode="random",
            total_score=100,
            duration=120,
            question_ids=[1, 2, 3],
        )
        db.add(exam)
        db.add(
            ExamSession(
                session_id="s1",
                user_id=1,
                exam_id=1,
                status=ExamStatus.COMPLETED.value,
                answers={},
                score=70,
                correct_count=2,
                total_count=3,
                start_time=datetime(2026, 6, 1),
                submitted_at=datetime(2026, 6, 1),
            )
        )
        db.add(
            WrongQuestion(
                user_id=1,
                question_id=2,
                session_id="s1",
                user_answer="B",
                wrong_count=1,
                last_wrong_at=datetime(2026, 6, 1),
            )
        )
        db.commit()

        result = AnalysisService(db).get_score_trends(user_id=1, subject_id=1)

        assert result["summary"]["sessions"] == 1
        assert result["summary"]["average_score_rate"] == 70
        assert result["subjects"][0]["subject_name"] == "马克思主义基本原理概论"
        chapters = {item["chapter_name"]: item for item in result["chapters"]}
        assert chapters["第一章"]["score_rate"] == 50
        assert chapters["第二章"]["score_rate"] == 100
    finally:
        db.close()
