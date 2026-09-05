# -*- coding: utf-8 -*-
"""Algorithm-level tests for paper generation, analytics, and planning."""

from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.models.exam import Exam, ExamResult, ExamSession, ExamStatus, WrongQuestion
from backend.models.planner import DailyTask, StudyPlan
from backend.models.question import Difficulty, Question, QuestionType
from backend.services.analysis_service import AnalysisService
from backend.services.exam_engine import ExamEngine
from backend.services.planner_service import PlannerService
from backend.utils.rate_limit import RateLimiter
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


def test_exam_session_detail_restores_ordered_paper_and_answers() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add_all([
            _question(1, QuestionType.SINGLE_CHOICE.value, Difficulty.EASY.value, 1),
            _question(2, QuestionType.SINGLE_CHOICE.value, Difficulty.MEDIUM.value, 1),
        ])
        exam = Exam(subject_id=1, name="恢复测试", mode="random", question_ids=[2, 1], total_score=4, duration=90)
        db.add(exam)
        db.flush()
        db.add(
            ExamSession(
                session_id="resume-session",
                user_id=1,
                exam_id=exam.id,
                status=ExamStatus.IN_PROGRESS.value,
                answers={"2": "A"},
                start_time=datetime.now(),
                end_time=datetime.now() + timedelta(minutes=90),
            )
        )
        db.commit()

        detail = ExamEngine(db).get_session_detail("resume-session")
        assert detail["answers"] == {"2": "A"}
        assert detail["duration"] == 90
        assert [question["id"] for question in detail["paper"]["questions"]] == [2, 1]
        assert "answer" not in detail["paper"]["questions"][0]

        cancelled = ExamEngine(db).cancel_exam("resume-session")
        assert cancelled["status"] == ExamStatus.CANCELLED.value
    finally:
        db.close()


def test_completed_exam_detail_contains_score_review() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        question = _question(1, QuestionType.SINGLE_CHOICE.value, Difficulty.EASY.value, 1)
        db.add(question)
        exam = Exam(subject_id=1, name="结果回看", mode="random", question_ids=[1], total_score=2, duration=30)
        db.add(exam)
        db.flush()
        db.add(
            ExamSession(
                session_id="completed-session",
                user_id=1,
                exam_id=exam.id,
                status=ExamStatus.COMPLETED.value,
                answers={"1": "A"},
                score=2,
                start_time=datetime.now(),
                submitted_at=datetime.now(),
            )
        )
        db.commit()

        detail = ExamEngine(db).get_session_detail("completed-session")
        assert detail["result"]["score"] == 2
        assert detail["result"]["question_analysis"][0]["correct_answer"] == "A"
        assert db.query(ExamResult).filter(ExamResult.session_id == "completed-session").count() == 1
    finally:
        db.close()


def test_repeated_exam_submission_is_idempotent() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(_question(1, QuestionType.SINGLE_CHOICE.value, Difficulty.EASY.value, 1))
        exam = Exam(subject_id=1, name="幂等交卷", mode="random", question_ids=[1], total_score=2, duration=30)
        db.add(exam)
        db.flush()
        db.add(
            ExamSession(
                session_id="idempotent-session",
                user_id=1,
                exam_id=exam.id,
                status=ExamStatus.IN_PROGRESS.value,
                answers={"1": "B"},
                start_time=datetime.now(),
            )
        )
        db.commit()

        service = ExamEngine(db)
        first = service.submit_paper("idempotent-session")
        second = service.submit_paper("idempotent-session")
        wrong = db.query(WrongQuestion).filter(WrongQuestion.user_id == 1, WrongQuestion.question_id == 1).one()
        assert first == second
        assert wrong.wrong_count == 1
    finally:
        db.close()


def test_timeout_exam_can_still_be_scored_once() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        db.add(_question(1, QuestionType.SINGLE_CHOICE.value, Difficulty.EASY.value, 1))
        exam = Exam(subject_id=1, name="timeout", mode="random", question_ids=[1], total_score=2, duration=30)
        db.add(exam)
        db.flush()
        db.add(ExamSession(
            session_id="timeout-session",
            user_id=1,
            exam_id=exam.id,
            status=ExamStatus.TIMEOUT.value,
            answers={"1": "A"},
            start_time=datetime.now() - timedelta(minutes=31),
            end_time=datetime.now() - timedelta(minutes=1),
        ))
        db.commit()

        service = ExamEngine(db)
        assert "result" not in service.get_session_detail("timeout-session")
        first = service.submit_paper("timeout-session")
        second = service.submit_paper("timeout-session")
        session = db.query(ExamSession).filter(ExamSession.session_id == "timeout-session").one()
        assert first == second
        assert first["score"] == 2
        assert session.status == ExamStatus.TIMEOUT.value
        assert db.query(ExamResult).filter(ExamResult.session_id == "timeout-session").count() == 1
    finally:
        db.close()


def test_planner_progress_can_be_completed_and_reopened() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        plan = StudyPlan(
            user_id=1,
            exam_date=datetime.now() + timedelta(days=30),
            daily_hours=2,
            subjects=[1],
            plan_data={},
            status="active",
        )
        db.add(plan)
        db.flush()
        task = DailyTask(plan_id=plan.id, user_id=1, task_date=datetime.now(), subject_id=1)
        db.add(task)
        db.commit()

        service = PlannerService(db)
        completed = service.update_progress(1, [{"id": task.id, "is_completed": True, "actual_hours": 1.5}])
        db.refresh(task)
        assert task.is_completed is True
        assert completed["completion_rate"] == 100

        reopened = service.update_progress(1, [{"id": task.id, "is_completed": False}])
        db.refresh(task)
        assert task.is_completed is False
        assert task.completion_time is None
        assert reopened["completion_rate"] == 0
    finally:
        db.close()


def test_existing_long_plan_syncs_tasks_beyond_day_thirty() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        later = today + timedelta(days=45)
        plan = StudyPlan(
            user_id=1,
            exam_date=today + timedelta(days=60),
            daily_hours=2,
            subjects=[1],
            plan_data={
                "tasks": [
                    {"date": today.isoformat(), "subject_id": 1, "chapter_ids": [], "question_count": 10, "video_ids": [], "review_points": []},
                    {"date": later.isoformat(), "subject_id": 1, "chapter_ids": [], "question_count": 12, "video_ids": [], "review_points": []},
                ]
            },
            status="active",
        )
        db.add(plan)
        db.flush()
        db.add(DailyTask(plan_id=plan.id, user_id=1, task_date=today, subject_id=1, question_count=10))
        db.commit()

        tasks = PlannerService(db).get_daily_tasks(1, later)
        assert len(tasks) == 1
        assert tasks[0]["question_count"] == 12
        assert db.query(DailyTask).filter(DailyTask.plan_id == plan.id).count() == 2
    finally:
        db.close()


def test_archived_plan_can_be_restored_with_its_progress() -> None:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        exam_date = datetime.now() + timedelta(days=60)
        archived = StudyPlan(user_id=1, exam_date=exam_date, daily_hours=2, subjects=[1], plan_data={}, status="archived")
        active = StudyPlan(user_id=1, exam_date=exam_date, daily_hours=3, subjects=[2], plan_data={}, status="active")
        db.add_all([archived, active])
        db.flush()
        db.add_all([
            DailyTask(plan_id=archived.id, user_id=1, task_date=datetime.now(), subject_id=1, is_completed=True),
            DailyTask(plan_id=active.id, user_id=1, task_date=datetime.now(), subject_id=2),
        ])
        db.commit()

        service = PlannerService(db)
        history = service.get_plan_history(1)
        restored = service.activate_plan(1, archived.id)
        db.refresh(active)
        assert history["total"] == 2
        assert "plan_data" not in history["items"][0]
        assert restored["status"] == "active"
        assert restored["completion_rate"] == 100
        assert active.status == "archived"

        assert service.delete_archived_plan(1, active.id) is True
        assert db.query(StudyPlan).filter(StudyPlan.id == active.id).count() == 0
        assert db.query(DailyTask).filter(DailyTask.plan_id == active.id).count() == 0
        with pytest.raises(ValueError, match="active"):
            service.delete_archived_plan(1, archived.id)
    finally:
        db.close()


def test_rate_limiter_uses_local_fallback_when_redis_is_unavailable() -> None:
    class OfflineRedis:
        @staticmethod
        def increment_with_expiry(key: str, expire: int):
            return None

    limiter = RateLimiter(OfflineRedis())
    limiter.check("test", "unique-user", limit=2, window_seconds=60)
    limiter.check("test", "unique-user", limit=2, window_seconds=60)
    with pytest.raises(HTTPException) as exc_info:
        limiter.check("test", "unique-user", limit=2, window_seconds=60)
    assert getattr(exc_info.value, "status_code", None) == 429


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
