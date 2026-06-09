# -*- coding: utf-8 -*-
"""Study plan service."""

from collections import Counter
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
        due_reviews_by_date = self._due_reviews_by_date(user_id, subjects, today, days)
        tasks = self._build_daily_tasks(
            user_id=user_id,
            subjects=subjects,
            start=today,
            days=days,
            daily_hours=daily_hours,
            weak_points_by_subject=weak_points_by_subject,
            high_freq_by_subject=high_freq_by_subject,
            due_reviews_by_date=due_reviews_by_date,
        )
        allocation = self.allocate_time(
            days,
            daily_hours,
            [point for points in weak_points_by_subject.values() for point in points],
            [point for points in high_freq_by_subject.values() for point in points],
        )
        plan_system = self._build_system_plan(
            start=today,
            days=days,
            subjects=subjects,
            daily_hours=daily_hours,
            weak_points_by_subject=weak_points_by_subject,
            high_freq_by_subject=high_freq_by_subject,
            due_reviews_by_date=due_reviews_by_date,
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
            plan_data={
                "tasks": tasks,
                "days": days,
                "allocation": allocation,
                **plan_system,
            },
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
            now = datetime.now()
            weak_items = [
                {
                    "point_id": point.id,
                    "name": point.name,
                    "description": point.description,
                    "chapter_id": point.chapter_id,
                    "mastery_level": mastery.mastery_level,
                    "correct_count": mastery.correct_count,
                    "wrong_count": mastery.wrong_count,
                    "next_review_time": mastery.next_review_time.isoformat() if mastery.next_review_time else None,
                    "is_due": bool(mastery.next_review_time and mastery.next_review_time <= now),
                    "priority": "high"
                    if mastery.mastery_level < 0.6 or (mastery.next_review_time and mastery.next_review_time <= now)
                    else "medium",
                    "reason": "掌握度低于 60%，优先安排概念重建和错题复盘"
                    if mastery.mastery_level < 0.6
                    else "掌握度未达稳定水平，安排间隔复习",
                }
                for mastery, point in mastery_rows
                if mastery.mastery_level < 0.8
            ]
            weak_items.sort(
                key=lambda item: (
                    0 if item.get("priority") == "high" else 1,
                    0 if item.get("is_due") else 1,
                    item.get("mastery_level", 1),
                    -int(item.get("wrong_count") or 0),
                )
            )
            return weak_items[:10]

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
                    "description": point.description,
                    "chapter_id": point.chapter_id,
                    "mastery_level": max(0.2, round(1 - min(wrong_total, 5) / 6, 2)),
                    "wrong_count": wrong_total,
                    "priority": "high" if wrong_total >= 2 or point.frequency >= 6 else "medium",
                    "reason": f"错题累计 {wrong_total} 次，建议先复盘概念再做同类题",
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
                "description": point.description,
                "chapter_id": point.chapter_id,
                "mastery_level": 0.65,
                "priority": "high" if point.frequency >= 6 else "medium",
                "reason": "暂无个人做题记录，按高频考点先行纳入计划",
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
                    "interval_days": interval,
                    "review_type": "ebbinghaus",
                    "review_points": learned_points,
                }
            )
        return schedule

    def _due_reviews_by_date(
        self,
        user_id: int,
        subjects: List[int],
        start: datetime,
        days: int,
    ) -> Dict[str, List[Dict[str, Any]]]:
        if not subjects:
            return {}

        end = start + timedelta(days=max(0, min(days, 60) - 1))
        rows = (
            self.db.query(UserMastery, KnowledgePoint, Chapter)
            .join(KnowledgePoint, UserMastery.knowledge_point_id == KnowledgePoint.id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(
                UserMastery.user_id == user_id,
                Chapter.subject_id.in_(subjects),
                UserMastery.next_review_time.isnot(None),
                UserMastery.next_review_time <= end,
            )
            .all()
        )

        schedule: Dict[str, List[Dict[str, Any]]] = {}
        for mastery, point, chapter in rows:
            due_time = mastery.next_review_time or start
            due_date = max(due_time.date(), start.date())
            key = due_date.isoformat()
            schedule.setdefault(key, []).append(
                {
                    "id": point.id,
                    "point_id": point.id,
                    "name": point.name,
                    "chapter_id": point.chapter_id,
                    "subject_id": chapter.subject_id,
                    "mastery_level": mastery.mastery_level,
                    "wrong_count": mastery.wrong_count,
                    "next_review_time": due_time.isoformat(),
                    "review_type": "due",
                    "priority": "high" if mastery.mastery_level < 0.6 else "medium",
                    "reason": "艾宾浩斯间隔复习到期",
                }
            )

        for review_points in schedule.values():
            review_points.sort(
                key=lambda item: (
                    0 if item.get("priority") == "high" else 1,
                    item.get("mastery_level", 1),
                    -int(item.get("wrong_count") or 0),
                )
            )
        return schedule

    def _build_review_schedule(
        self,
        start: datetime,
        high_freq_points: List[Dict[str, Any]],
        due_reviews_by_date: Dict[str, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        schedule = self.schedule_reviews(start, high_freq_points)
        for date, review_points in due_reviews_by_date.items():
            schedule.append(
                {
                    "date": date,
                    "review_type": "mastery_due",
                    "review_points": self._merge_review_points(review_points, limit=8),
                }
            )
        schedule.sort(key=lambda item: item["date"])
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
        user_id: int,
        subjects: List[int],
        start: datetime,
        days: int,
        daily_hours: float,
        weak_points_by_subject: Dict[int, List[Dict[str, Any]]],
        high_freq_by_subject: Dict[int, List[Dict[str, Any]]],
        due_reviews_by_date: Dict[str, List[Dict[str, Any]]],
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
            task_date = start + timedelta(days=offset)
            date_key = task_date.date().isoformat()
            due_reviews = due_reviews_by_date.get(date_key, [])
            if due_reviews:
                subject_counts = Counter(
                    int(item["subject_id"]) for item in due_reviews if item.get("subject_id")
                )
                subject_id = subject_counts.most_common(1)[0][0] if subject_counts else priority_subjects[0]
            else:
                subject_id = priority_subjects[offset % len(priority_subjects)]

            subject_due_reviews = [
                item for item in due_reviews if int(item.get("subject_id") or 0) == int(subject_id)
            ]
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
            target_chapter_id = (
                subject_due_reviews[0].get("chapter_id")
                if subject_due_reviews
                else target_point.get("chapter_id") if target_point else None
            )
            chapter = next((item for item in chapters if item.id == target_chapter_id), None)
            if not chapter:
                chapter = chapters[offset % len(chapters)] if chapters else None

            review_points = self._merge_review_points(
                subject_due_reviews,
                self._build_review_points(target_point),
            )
            if chapter and not review_points:
                points = (
                    self.db.query(KnowledgePoint)
                    .filter(KnowledgePoint.chapter_id == chapter.id)
                    .order_by(KnowledgePoint.frequency.desc())
                    .limit(3)
                    .all()
                )
                review_points = [{"id": point.id, "name": point.name} for point in points]

            is_mock_day = self._is_mock_exam_day(offset, days)
            is_sprint_day = offset >= max(0, days - 7)
            task_type = (
                "全真模考"
                if is_mock_day
                else "冲刺回顾"
                if is_sprint_day
                else "间隔复习"
                if subject_due_reviews
                else self._task_type(offset)
            )
            focus_blocks = (
                self._build_mock_focus_blocks(daily_hours)
                if is_mock_day
                else self._build_sprint_focus_blocks(daily_hours, review_points)
                if is_sprint_day
                else self._build_focus_blocks(daily_hours, review_points)
            )
            question_count = (
                max(30, int(daily_hours * 18))
                if is_mock_day
                else max(20, int(daily_hours * 15))
                if is_sprint_day
                else max(10, int(daily_hours * (10 if subject_due_reviews else 12)))
            )
            chapter_ids = [chapter.id] if chapter else []
            tasks.append(
                {
                    "date": task_date.isoformat(),
                    "subject_id": subject_id,
                    "chapter_ids": chapter_ids,
                    "task_type": task_type,
                    "estimated_hours": daily_hours,
                    "question_count": question_count,
                    "video_ids": self._recommend_video_ids(subject_id, chapter_ids),
                    "review_points": review_points,
                    "focus_blocks": focus_blocks,
                }
            )
        return tasks

    def _build_system_plan(
        self,
        start: datetime,
        days: int,
        subjects: List[int],
        daily_hours: float,
        weak_points_by_subject: Dict[int, List[Dict[str, Any]]],
        high_freq_by_subject: Dict[int, List[Dict[str, Any]]],
        due_reviews_by_date: Dict[str, List[Dict[str, Any]]],
    ) -> Dict[str, Any]:
        all_weak_points = [point for points in weak_points_by_subject.values() for point in points]
        all_high_freq = [point for points in high_freq_by_subject.values() for point in points]
        return {
            "phases": self._build_phases(start, days),
            "weekly_goals": self._build_weekly_goals(start, days, subjects, weak_points_by_subject, high_freq_by_subject),
            "daily_template": self._build_focus_blocks(daily_hours, all_weak_points[:2] or all_high_freq[:2]),
            "milestones": self._build_milestones(start, days),
            "mock_exams": self._build_mock_exam_schedule(start, days, subjects),
            "sprint_plan": self._build_sprint_plan(start, days, all_weak_points, all_high_freq),
            "review_schedule": self._build_review_schedule(start, all_high_freq[:8], due_reviews_by_date),
            "resource_strategy": self._build_resource_strategy(),
            "risk_alerts": self._build_risk_alerts(days, daily_hours, all_weak_points),
        }

    @staticmethod
    def _build_phases(start: datetime, days: int) -> List[Dict[str, Any]]:
        phase_defs = [
            ("基础梳理", 0.0, 0.35, "通读教材和考试大纲，建立章节框架，完成高频概念卡片。"),
            ("强化训练", 0.35, 0.68, "按章节刷题，针对薄弱点进行同类题训练，形成错题归因。"),
            ("套卷模拟", 0.68, 0.88, "每周至少完成 1 套限时卷，复盘失分点和答题时间分配。"),
            ("冲刺回顾", 0.88, 1.0, "压缩记忆清单，重做错题和高频简答题，保持考试节奏。"),
        ]
        phases = []
        for name, start_ratio, end_ratio, goal in phase_defs:
            start_offset = min(days - 1, max(0, int(days * start_ratio)))
            end_offset = min(days - 1, max(start_offset, int(days * end_ratio) - 1))
            phases.append(
                {
                    "name": name,
                    "start_date": (start + timedelta(days=start_offset)).date().isoformat(),
                    "end_date": (start + timedelta(days=end_offset)).date().isoformat(),
                    "goal": goal,
                }
            )
        return phases

    @staticmethod
    def _build_weekly_goals(
        start: datetime,
        days: int,
        subjects: List[int],
        weak_points_by_subject: Dict[int, List[Dict[str, Any]]],
        high_freq_by_subject: Dict[int, List[Dict[str, Any]]],
    ) -> List[Dict[str, Any]]:
        weeks = min(12, max(1, (days + 6) // 7))
        goals = []
        for week in range(weeks):
            subject_id = subjects[week % len(subjects)] if subjects else None
            weak_points = weak_points_by_subject.get(subject_id, []) if subject_id else []
            high_freq = high_freq_by_subject.get(subject_id, []) if subject_id else []
            focus_points = weak_points[:2] or high_freq[:2]
            goals.append(
                {
                    "week": week + 1,
                    "start_date": (start + timedelta(days=week * 7)).date().isoformat(),
                    "subject_id": subject_id,
                    "focus_points": [
                        {"id": point.get("point_id") or point.get("id"), "name": point["name"]}
                        for point in focus_points
                    ],
                    "target": "完成章节框架复盘、30-60 道对应训练题、1 次错题归因。",
                }
            )
        return goals

    @staticmethod
    def _build_milestones(start: datetime, days: int) -> List[Dict[str, Any]]:
        checkpoints = [
            (0.25, "完成教材第一轮框架梳理"),
            (0.5, "完成高频考点第一轮刷题"),
            (0.75, "完成至少 2 次限时模拟并复盘"),
            (0.95, "完成错题本和简答题模板冲刺"),
        ]
        return [
            {
                "date": (start + timedelta(days=min(days - 1, max(0, int(days * ratio))))).date().isoformat(),
                "title": title,
                "check": "检查完成率、错题数量和主观题表达完整度",
            }
            for ratio, title in checkpoints
        ]

    @staticmethod
    def _is_mock_exam_day(offset: int, days: int) -> bool:
        if days < 7:
            return offset == days - 1
        if offset >= max(0, days - 14) and offset % 3 == 0:
            return True
        return (offset + 1) % 7 == 0 and offset >= max(0, int(days * 0.35))

    @staticmethod
    def _build_mock_exam_schedule(start: datetime, days: int, subjects: List[int]) -> List[Dict[str, Any]]:
        schedule: List[Dict[str, Any]] = []
        if not subjects:
            return schedule
        for offset in range(min(days, 60)):
            if not PlannerService._is_mock_exam_day(offset, days):
                continue
            subject_id = subjects[len(schedule) % len(subjects)]
            schedule.append(
                {
                    "date": (start + timedelta(days=offset)).date().isoformat(),
                    "subject_id": subject_id,
                    "title": "限时全真模考",
                    "duration_minutes": 150,
                    "review_focus": ["时间分配", "错题归因", "主观题表达完整度"],
                }
            )
        return schedule

    @staticmethod
    def _build_sprint_plan(
        start: datetime,
        days: int,
        weak_points: List[Dict[str, Any]],
        high_freq_points: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        sprint_start = start + timedelta(days=max(0, days - 7))
        focus_points = weak_points[:4] or high_freq_points[:4]
        daily_actions = [
            "压缩高频概念清单，保留必须背诵和易混淆条目",
            "重做错题和同类题，记录仍未稳定掌握的考点",
            "完成一套限时卷，复盘时间分配和失分题型",
            "主观题模板演练，按评分点补齐概念、依据和结论",
            "高频考点快速回看，减少新内容摄入",
            "错题本最后一轮归因，确认下次复习时间",
            "轻量回顾，保持作息和考试节奏",
        ]
        return [
            {
                "date": (sprint_start + timedelta(days=index)).date().isoformat(),
                "day": index + 1,
                "action": action,
                "focus_points": [
                    {"id": point.get("point_id") or point.get("id"), "name": point.get("name")}
                    for point in focus_points[index % len(focus_points) : index % len(focus_points) + 1]
                ]
                if focus_points
                else [],
            }
            for index, action in enumerate(daily_actions[: min(7, max(days, 1))])
        ]

    @staticmethod
    def _build_focus_blocks(daily_hours: float, review_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        core_minutes = int(max(20, daily_hours * 60 * 0.45))
        practice_minutes = int(max(20, daily_hours * 60 * 0.35))
        review_minutes = max(15, int(daily_hours * 60) - core_minutes - practice_minutes)
        focus_names = "、".join(point.get("name", "") for point in review_points[:2] if point.get("name")) or "当日章节重点"
        return [
            {"name": "概念精读", "minutes": core_minutes, "content": f"精读并复述：{focus_names}"},
            {"name": "题目训练", "minutes": practice_minutes, "content": "完成客观题训练并记录错因"},
            {"name": "错题复盘", "minutes": review_minutes, "content": "按概念不清、审题偏差、表达缺项三类整理"},
        ]

    @staticmethod
    def _build_mock_focus_blocks(daily_hours: float) -> List[Dict[str, Any]]:
        total_minutes = int(max(90, daily_hours * 60))
        exam_minutes = min(150, int(total_minutes * 0.65))
        review_minutes = max(30, total_minutes - exam_minutes)
        return [
            {"name": "限时模考", "minutes": exam_minutes, "content": "按正式考试时间和题序完成整卷"},
            {"name": "错题归因", "minutes": review_minutes, "content": "按章节、题型、审题和表达缺项归类复盘"},
        ]

    @staticmethod
    def _build_sprint_focus_blocks(daily_hours: float, review_points: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        total_minutes = int(max(60, daily_hours * 60))
        checklist_minutes = int(total_minutes * 0.35)
        drill_minutes = int(total_minutes * 0.4)
        review_minutes = max(20, total_minutes - checklist_minutes - drill_minutes)
        focus_names = "、".join(point.get("name", "") for point in review_points[:2] if point.get("name")) or "高频考点"
        return [
            {"name": "冲刺清单", "minutes": checklist_minutes, "content": f"快速回看：{focus_names}"},
            {"name": "限时刷题", "minutes": drill_minutes, "content": "只做高频题、错题和主观题模板题"},
            {"name": "考前复盘", "minutes": review_minutes, "content": "压缩记忆负担，确认易错点和答题节奏"},
        ]

    @staticmethod
    def _build_resource_strategy() -> List[Dict[str, str]]:
        return [
            {"type": "官方信息", "action": "考试时间、报名和政策以教育部教育考试院及各省教育考试院公告为准。"},
            {"type": "教材框架", "action": "先按章节目录建立知识树，再把高频考点挂到对应章节。"},
            {"type": "视频资源", "action": "只用于理解难点，观看后必须回到题目训练验证掌握度。"},
            {"type": "错题本", "action": "错题必须写清错因、关联考点和下次复习日期。"},
        ]

    @staticmethod
    def _build_risk_alerts(days: int, daily_hours: float, weak_points: List[Dict[str, Any]]) -> List[str]:
        alerts = []
        if days < 30:
            alerts.append("备考周期少于 30 天，应压缩教材通读时间，优先处理高频考点和错题。")
        if daily_hours < 2:
            alerts.append("每日学习时长低于 2 小时，建议周末补一次 2 小时套卷训练。")
        high_priority_count = len([point for point in weak_points if point.get("priority") == "high"])
        if high_priority_count >= 3:
            alerts.append(f"高优先级薄弱点 {high_priority_count} 个，前两周应优先安排概念重建。")
        return alerts or ["当前时间配置较均衡，按周目标推进并保持错题复盘即可。"]

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
        ranked = sorted(
            candidates,
            key=lambda item: (
                0 if item.get("priority") == "high" else 1,
                item.get("mastery_level", 0.65),
                -int(item.get("frequency") or 0),
            ),
        )
        return ranked[offset % len(ranked)]

    @staticmethod
    def _task_type(offset: int) -> str:
        cycle = offset % 7
        if cycle in {0, 1, 2}:
            return "基础巩固"
        if cycle in {3, 4}:
            return "强化刷题"
        if cycle == 5:
            return "错题复盘"
        return "周测总结"

    @staticmethod
    def _build_review_points(target_point: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not target_point:
            return []
        point_id = target_point.get("point_id") or target_point.get("id")
        if not point_id:
            return []
        return [{"id": point_id, "name": target_point["name"]}]

    @staticmethod
    def _merge_review_points(*groups: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        merged: List[Dict[str, Any]] = []
        seen = set()
        for group in groups:
            for item in group:
                point_id = item.get("point_id") or item.get("id")
                if not point_id or point_id in seen:
                    continue
                seen.add(point_id)
                merged.append(
                    {
                        "id": point_id,
                        "name": item.get("name", ""),
                        "chapter_id": item.get("chapter_id"),
                        "mastery_level": item.get("mastery_level"),
                        "review_type": item.get("review_type", "focus"),
                    }
                )
                if len(merged) >= limit:
                    return merged
        return merged

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
            "focus_blocks": PlannerService._build_focus_blocks(
                task.actual_hours or 2,
                task.review_points or [],
            ),
            "is_completed": task.is_completed,
            "actual_hours": task.actual_hours,
        }
