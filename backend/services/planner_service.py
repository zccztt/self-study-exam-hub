# -*- coding: utf-8 -*-
"""Study plan service."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.exam import WrongQuestion
from backend.models.planner import DailyTask, StudyPlan, UserMastery
from backend.models.question import Question
from backend.models.video import Video
from backend.services.analysis_service import AnalysisService


class PlannerService:
    def __init__(self, db: Session):
        self.db = db

    def generate_study_plan(
        self,
        user_id: int,
        exam_date: datetime,
        subjects: List[int],
        daily_hours: float,
        preferences: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        preferences = preferences or {}
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        days = max((exam_date.date() - today.date()).days, 1)
        weak_points_by_subject = {
            subject_id: self.identify_weak_points(user_id, subject_id)
            for subject_id in subjects
        }
        high_freq_by_subject = {
            subject_id: AnalysisService(self.db).get_high_frequency_points(subject_id, limit=20)
            for subject_id in subjects
        }
        tasks = self._build_daily_tasks(
            subjects=subjects,
            start=today,
            days=days,
            daily_hours=daily_hours,
            weak_points_by_subject=weak_points_by_subject,
            high_freq_by_subject=high_freq_by_subject,
        )
        allocation = self.allocate_time(
            days,
            daily_hours,
            [point for points in weak_points_by_subject.values() for point in points],
            [point for points in high_freq_by_subject.values() for point in points],
        )
        expected_pass_rate = self._estimate_pass_rate(days, daily_hours, weak_points_by_subject)

        self.db.query(StudyPlan).filter(
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active",
        ).update({"status": "archived"})

        plan = StudyPlan(
            user_id=user_id,
            exam_date=exam_date,
            daily_hours=daily_hours,
            subjects=subjects,
            preferences=preferences,
            plan_data={"tasks": tasks, "days": days, "allocation": allocation},
            expected_pass_rate=round(expected_pass_rate, 2),
        )
        self.db.add(plan)
        self.db.commit()
        self.db.refresh(plan)

        for task in tasks[: min(days, 30)]:
            self.db.add(
                DailyTask(
                    plan_id=plan.id,
                    user_id=user_id,
                    task_date=datetime.fromisoformat(task["date"]),
                    subject_id=task["subject_id"],
                    chapter_ids=task["chapter_ids"],
                    question_count=task["question_count"],
                    video_ids=task["video_ids"],
                    review_points=task["review_points"],
                )
            )
        self.db.commit()

        return self._serialize_plan(plan)

    def identify_weak_points(self, user_id: int, subject_id: int) -> List[Dict[str, Any]]:
        mastery_rows = (
            self.db.query(UserMastery, KnowledgePoint)
            .join(KnowledgePoint, UserMastery.knowledge_point_id == KnowledgePoint.id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(UserMastery.user_id == user_id, Chapter.subject_id == subject_id)
            .all()
        )
        if mastery_rows:
            return [
                {
                    "point_id": point.id,
                    "name": point.name,
                    "chapter_id": point.chapter_id,
                    "mastery_level": mastery.mastery_level,
                    "correct_count": mastery.correct_count,
                    "wrong_count": mastery.wrong_count,
                    "next_review_time": mastery.next_review_time.isoformat() if mastery.next_review_time else None,
                    "priority": "high" if mastery.mastery_level < 0.6 else "medium",
                }
                for mastery, point in mastery_rows
                if mastery.mastery_level < 0.8
            ][:10]

        wrong_rows = (
            self.db.query(KnowledgePoint, func.count(WrongQuestion.id).label("wrong_total"))
            .join(QuestionKnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
            .join(Question, QuestionKnowledgePoint.question_id == Question.id)
            .join(WrongQuestion, WrongQuestion.question_id == Question.id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_mastered.is_(False),
                Chapter.subject_id == subject_id,
            )
            .group_by(KnowledgePoint.id)
            .order_by(func.count(WrongQuestion.id).desc(), KnowledgePoint.frequency.desc())
            .limit(10)
            .all()
        )
        if wrong_rows:
            return [
                {
                    "point_id": point.id,
                    "name": point.name,
                    "chapter_id": point.chapter_id,
                    "mastery_level": max(0.2, round(1 - min(wrong_total, 5) / 6, 2)),
                    "wrong_count": wrong_total,
                    "priority": "high" if wrong_total >= 2 or point.frequency >= 6 else "medium",
                }
                for point, wrong_total in wrong_rows
            ]

        points = (
            self.db.query(KnowledgePoint)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(Chapter.subject_id == subject_id)
            .order_by(KnowledgePoint.frequency.desc())
            .limit(5)
            .all()
        )
        return [
            {
                "point_id": point.id,
                "name": point.name,
                "chapter_id": point.chapter_id,
                "mastery_level": 0.65,
                "priority": "high" if point.frequency >= 6 else "medium",
            }
            for point in points
        ]

    def allocate_time(
        self,
        total_days: int,
        daily_hours: float,
        weak_points: List[Dict[str, Any]],
        high_freq_points: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        total_hours = max(total_days, 1) * daily_hours
        weak_weight = 0.5 if weak_points else 0.3
        high_freq_weight = 0.35 if high_freq_points else 0.45
        weak_hours = round(total_hours * weak_weight, 1)
        high_freq_hours = round(total_hours * high_freq_weight, 1)
        review_hours = round(total_hours - weak_hours - high_freq_hours, 1)
        return {
            "total_hours": round(total_hours, 1),
            "weak_points_hours": weak_hours,
            "high_frequency_hours": high_freq_hours,
            "review_hours": review_hours,
            "weak_points": self._allocate_items(weak_points, weak_hours),
            "high_frequency_points": self._allocate_items(high_freq_points, high_freq_hours),
        }

    def schedule_reviews(self, start_date: datetime, learned_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        intervals = [1, 3, 7, 15, 30]
        schedule = []
        for interval in intervals:
            schedule.append(
                {
                    "date": (start_date + timedelta(days=interval)).date().isoformat(),
                    "review_points": learned_points,
                }
            )
        return schedule

    def update_progress(self, user_id: int, completed_tasks: List[Dict[str, Any]]) -> Dict[str, Any]:
        task_ids = [task["id"] for task in completed_tasks if task.get("id")]
        if task_ids:
            tasks = self.db.query(DailyTask).filter(DailyTask.user_id == user_id, DailyTask.id.in_(task_ids)).all()
            for task in tasks:
                task.is_completed = True
                task.completion_time = datetime.now()
                matching_payload = next((item for item in completed_tasks if item.get("id") == task.id), {})
                if matching_payload.get("actual_hours") is not None:
                    task.actual_hours = float(matching_payload["actual_hours"])
            self.db.commit()

        active_task_query = (
            self.db.query(DailyTask)
            .join(StudyPlan, DailyTask.plan_id == StudyPlan.id)
            .filter(DailyTask.user_id == user_id, StudyPlan.status == "active")
        )
        total = active_task_query.count()
        done = active_task_query.filter(DailyTask.is_completed.is_(True)).count()
        completion_rate = round(done / total * 100, 2) if total else 0
        self.db.query(StudyPlan).filter(
            StudyPlan.user_id == user_id,
            StudyPlan.status == "active",
        ).update({"completion_rate": completion_rate})
        self.db.commit()
        return {"completion_rate": completion_rate, "completed": done, "total": total}

    def get_daily_tasks(self, user_id: int, date: datetime) -> List[Dict[str, Any]]:
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        tasks = (
            self.db.query(DailyTask)
            .join(StudyPlan, DailyTask.plan_id == StudyPlan.id)
            .filter(DailyTask.user_id == user_id, DailyTask.task_date >= day_start, DailyTask.task_date < day_end)
            .filter(StudyPlan.status == "active")
            .order_by(DailyTask.id.asc())
            .all()
        )
        return [self._serialize_task(task) for task in tasks]

    def get_latest_plan(self, user_id: int) -> Optional[Dict[str, Any]]:
        plan = (
            self.db.query(StudyPlan)
            .filter(StudyPlan.user_id == user_id, StudyPlan.status == "active")
            .order_by(StudyPlan.created_at.desc())
            .first()
        )
        return self._serialize_plan(plan) if plan else None

    def _build_daily_tasks(
        self,
        subjects: List[int],
        start: datetime,
        days: int,
        daily_hours: float,
        weak_points_by_subject: Dict[int, List[Dict[str, Any]]],
        high_freq_by_subject: Dict[int, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        if not subjects:
            return []

        tasks: List[Dict[str, Any]] = []
        priority_subjects = sorted(
            subjects,
            key=lambda subject_id: (
                len([point for point in weak_points_by_subject.get(subject_id, []) if point.get("priority") == "high"]),
                len(weak_points_by_subject.get(subject_id, [])),
            ),
            reverse=True,
        )
        for offset in range(min(days, 60)):
            subject_id = priority_subjects[offset % len(priority_subjects)]
            target_point = self._select_target_point(
                offset,
                weak_points_by_subject.get(subject_id, []),
                high_freq_by_subject.get(subject_id, []),
            )
            chapters = (
                self.db.query(Chapter)
                .filter(Chapter.subject_id == subject_id)
                .order_by(Chapter.order.asc(), Chapter.id.asc())
                .all()
            )
            target_chapter_id = target_point.get("chapter_id") if target_point else None
            chapter = next((item for item in chapters if item.id == target_chapter_id), None)
            if not chapter:
                chapter = chapters[offset % len(chapters)] if chapters else None

            review_points = self._build_review_points(target_point)
            if chapter and not review_points:
                points = (
                    self.db.query(KnowledgePoint)
                    .filter(KnowledgePoint.chapter_id == chapter.id)
                    .order_by(KnowledgePoint.frequency.desc())
                    .limit(3)
                    .all()
                )
                review_points = [{"id": point.id, "name": point.name} for point in points]

            chapter_ids = [chapter.id] if chapter else []
            tasks.append(
                {
                    "date": (start + timedelta(days=offset)).isoformat(),
                    "subject_id": subject_id,
                    "chapter_ids": chapter_ids,
                    "question_count": max(10, int(daily_hours * 12)),
                    "video_ids": self._recommend_video_ids(subject_id, chapter_ids),
                    "review_points": review_points,
                }
            )
        return tasks

    def _recommend_video_ids(self, subject_id: int, chapter_ids: List[int], limit: int = 2) -> List[int]:
        query = self.db.query(Video.id).filter(Video.subject_id == subject_id, Video.is_active == 1)
        if chapter_ids:
            query = query.filter(Video.chapter_id.in_(chapter_ids))
        return [video_id for (video_id,) in query.order_by(Video.view_count.desc(), Video.id.desc()).limit(limit).all()]

    @staticmethod
    def _select_target_point(
        offset: int,
        weak_points: List[Dict[str, Any]],
        high_freq_points: List[Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        candidates = weak_points or high_freq_points
        if not candidates:
            return None
        return candidates[offset % len(candidates)]

    @staticmethod
    def _build_review_points(target_point: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not target_point:
            return []
        point_id = target_point.get("point_id") or target_point.get("id")
        if not point_id:
            return []
        return [{"id": point_id, "name": target_point["name"]}]

    @staticmethod
    def _allocate_items(items: List[Dict[str, Any]], hours: float) -> List[Dict[str, Any]]:
        if not items:
            return []
        per_item = round(hours / min(len(items), 5), 1) if hours > 0 else 0
        return [{**item, "allocated_hours": per_item} for item in items[:5]]

    @staticmethod
    def _estimate_pass_rate(
        days: int,
        daily_hours: float,
        weak_points_by_subject: Dict[int, List[Dict[str, Any]]],
    ) -> float:
        weak_points = [point for points in weak_points_by_subject.values() for point in points]
        average_mastery = (
            sum(point.get("mastery_level", 0.65) for point in weak_points) / len(weak_points)
            if weak_points
            else 0.7
        )
        time_factor = min(days, 90) / 220 + min(daily_hours, 6) / 24
        weakness_penalty = max(0, 0.75 - average_mastery) * 0.35
        return max(0.35, min(0.95, 0.5 + average_mastery * 0.25 + time_factor - weakness_penalty))

    @staticmethod
    def _serialize_plan(plan: StudyPlan) -> Dict[str, Any]:
        return {
            "id": plan.id,
            "user_id": plan.user_id,
            "exam_date": plan.exam_date.isoformat(),
            "daily_hours": plan.daily_hours,
            "subjects": plan.subjects,
            "preferences": plan.preferences or {},
            "plan_data": plan.plan_data or {},
            "status": plan.status,
            "completion_rate": plan.completion_rate,
            "expected_pass_rate": plan.expected_pass_rate,
            "created_at": plan.created_at.isoformat() if plan.created_at else None,
        }

    @staticmethod
    def _serialize_task(task: DailyTask) -> Dict[str, Any]:
        return {
            "id": task.id,
            "plan_id": task.plan_id,
            "user_id": task.user_id,
            "task_date": task.task_date.isoformat(),
            "subject_id": task.subject_id,
            "chapter_ids": task.chapter_ids or [],
            "question_count": task.question_count,
            "video_ids": task.video_ids or [],
            "review_points": task.review_points or [],
            "is_completed": task.is_completed,
            "actual_hours": task.actual_hours,
        }
