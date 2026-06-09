# -*- coding: utf-8 -*-
"""Algorithm-level tests for paper generation, analytics, and planning."""

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.models.exam import Exam, ExamSession, ExamStatus
from backend.models.question import Difficulty, Question, QuestionType
from backend.services.analysis_service import AnalysisService
from backend.services.exam_engine import ExamEngine
from backend.services.planner_service import PlannerService
from scripts.parse_paper import parse_paper_text


def _question(
    question_id: int,
    question_type: str,
    difficulty: str,
    chapter_id: int,
    frequency: int = 1,
) -> Question:
    question = Question(id=question_id, subject_id=1, content=f"Q{question_id}", answer="A")
    question.question_type = question_type
    question.difficulty = difficulty
    question.chapter_id = chapter_id
    question.frequency = frequency
    question.score = 2
    question.year = 2026
    return question


def test_constraint_greedy_paper_generation_satisfies_feasible_targets() -> None:
    questions = []
    question_id = 1
    for chapter_id in [1, 2, 3, 4]:
        for question_type in [QuestionType.SINGLE_CHOICE.value, QuestionType.MULTIPLE_CHOICE.value]:
            for difficulty in [Difficulty.EASY.value, Difficulty.MEDIUM.value, Difficulty.HARD.value]:
                questions.append(
                    _question(
                        question_id=question_id,
                        question_type=question_type,
                        difficulty=difficulty,
                        chapter_id=chapter_id,
                        frequency=(question_id % 5) + 1,
                    )
                )
                question_id += 1

    engine = ExamEngine.__new__(ExamEngine)
    selected, report = engine._select_questions_with_constraints(
        questions,
        10,
        {
            "constraints": {
                "question_type_ratio": {
                    QuestionType.SINGLE_CHOICE.value: 6,
                    QuestionType.MULTIPLE_CHOICE.value: 4,
                },
                "difficulty_ratio": {
                    Difficulty.EASY.value: 3,
                    Difficulty.MEDIUM.value: 5,
                    Difficulty.HARD.value: 2,
                },
                "chapter_coverage": 0.75,
                "chapter_ids": [1, 2, 3, 4],
            }
        },
    )

    assert len(selected) == 10
    assert report["question_type_actual"] == {
        QuestionType.SINGLE_CHOICE.value: 6,
        QuestionType.MULTIPLE_CHOICE.value: 4,
    }
    assert report["difficulty_actual"] == {
        Difficulty.MEDIUM.value: 5,
        Difficulty.EASY.value: 3,
        Difficulty.HARD.value: 2,
    }
    assert report["chapter_coverage_actual_count"] == 3
    assert report["chapter_coverage_target_count"] == 3
    assert report["satisfied"] is True


def test_recent_done_question_ids_reads_completed_exam_history() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        exam = Exam(
            subject_id=1,
            name="历史试卷",
            mode="random",
            question_ids=[11, 12, 13],
            total_score=6,
            duration=120,
        )
        db.add(exam)
        db.flush()
        db.add(
            ExamSession(
                session_id="session-1",
                user_id=1,
                exam_id=exam.id,
                status=ExamStatus.COMPLETED.value,
                answers={},
                start_time=datetime.now(),
                submitted_at=datetime.now(),
            )
        )
        db.commit()

        service = ExamEngine(db)
        assert service._recent_done_question_ids(1, {"user_id": 1}) == {11, 12, 13}
        assert service._recent_done_question_ids(2, {"user_id": 1}) == set()
    finally:
        db.close()


def test_linear_regression_trend_slope_detects_direction() -> None:
    assert AnalysisService._linear_regression_slope([1, 2, 3, 5]) > 0.3
    assert AnalysisService._linear_regression_slope([5, 3, 2, 1]) < -0.3
    assert AnalysisService._linear_regression_slope([2, 2, 2, 2]) == 0


def test_review_point_merge_deduplicates_due_and_focus_points() -> None:
    merged = PlannerService._merge_review_points(
        [{"id": 1, "name": "A", "review_type": "due"}],
        [{"id": 1, "name": "A"}, {"id": 2, "name": "B"}],
    )

    assert merged == [
        {"id": 1, "name": "A", "chapter_id": None, "mastery_level": None, "review_type": "due"},
        {"id": 2, "name": "B", "chapter_id": None, "mastery_level": None, "review_type": "focus"},
    ]


def test_parse_paper_text_extracts_choice_question() -> None:
    parsed = parse_paper_text(
        """
        1. 马克思主义鲜明特征包括哪一项？
        A. 科学性
        B. 随意性
        C. 片面性
        D. 偶然性
        答案：A
        解析：马克思主义具有科学性和实践性。
        """,
        subject_code="03709",
        subject_name="马克思主义基本原理概论",
        year=2024,
        month=10,
        source="测试真题",
        default_difficulty="medium",
    )

    assert len(parsed) == 1
    assert parsed[0]["question_type"] == QuestionType.SINGLE_CHOICE.value
    assert parsed[0]["options"] == ["科学性", "随意性", "片面性", "偶然性"]
    assert parsed[0]["answer"] == "A"
    assert parsed[0]["review_status"] == "pending"
