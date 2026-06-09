# -*- coding: utf-8 -*-
"""Algorithm-level tests for paper generation, analytics, and planning."""

from backend.models.question import Difficulty, Question, QuestionType
from backend.services.analysis_service import AnalysisService
from backend.services.exam_engine import ExamEngine
from backend.services.planner_service import PlannerService


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
