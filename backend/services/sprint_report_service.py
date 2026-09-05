# -*- coding: utf-8 -*-
"""Sprint report service for pre-exam review strategy generation."""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.exam import ExamResult, ExamSession, ExamStatus, WrongQuestion
from backend.models.planner import UserMastery
from backend.models.question import Question


class SprintReportService:
    """Generates a personalized pre-exam sprint report."""

    def __init__(self, db: Session):
        self.db = db

    def generate_report(
        self,
        user_id: int,
        subject_id: int,
        exam_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Generate a comprehensive pre-exam sprint report."""
        # === Data Collection ===
        high_freq_points = self._get_high_frequency_unmastered(user_id, subject_id)
        type_weakness = self._analyze_type_weakness(user_id, subject_id)
        score_history = self._get_recent_scores(user_id, subject_id)
        wrong_count = self._get_unmastered_wrong_count(user_id, subject_id)

        # === Calculate Assessment ===
        avg_score_rate = (
            sum(s["score_rate"] for s in score_history) / len(score_history)
            if score_history
            else 0
        )
        estimated_score = round(avg_score_rate * 100)
        days_remaining = (
            (exam_date.date() - date.today()).days if exam_date else None
        )

        # === Build Report ===
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "subject_id": subject_id,
            "exam_date": exam_date.isoformat() if exam_date else None,
            "days_remaining": days_remaining,

            # Current assessment
            "current_assessment": {
                "estimated_score": estimated_score,
                "pass_probability": self._estimate_pass_probability(avg_score_rate),
                "recent_trend": self._get_trend(score_history),
                "total_practice_count": len(score_history),
                "unmastered_wrong_count": wrong_count,
            },

            # Pass guarantee strategy
            "pass_strategy": self._build_pass_strategy(type_weakness),

            # Review checklist
            "review_checklist": {
                "must_review_points": high_freq_points[:10],
                "type_weakness": type_weakness[:3],
                "unmastered_wrong_count": wrong_count,
            },

            # Time allocation
            "time_allocation": self._build_time_allocation(
                days_remaining=days_remaining or 7,
                type_weakness=type_weakness,
                unmastered_count=len(high_freq_points),
            ),

            # Exam tips
            "exam_tips": {
                "time_management": "150分钟分配：选择题30分钟、填空题15分钟、简答题45分钟、论述题40分钟、检查20分钟",
                "answer_order": "先做选择→填空→简答→论述，确保容易拿的分先到手",
                "key_reminders": [
                    "多选题宁少选不多选（多选全错，少选得部分分）",
                    "简答题分点作答，每点标序号",
                    "论述题字数不低于300字，分层清晰",
                    "不留空白，不会的也写相关知识点",
                    "案例题每问必须有明确结论",
                ],
            },
        }

        return report

    def _get_high_frequency_unmastered(
        self, user_id: int, subject_id: int, limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get high-frequency knowledge points that the user hasn't mastered."""
        chapters = self.db.query(Chapter).filter(Chapter.subject_id == subject_id).all()
        chapter_ids = [ch.id for ch in chapters]
        if not chapter_ids:
            return []

        # Get all high-frequency points
        points = (
            self.db.query(KnowledgePoint)
            .filter(
                KnowledgePoint.chapter_id.in_(chapter_ids),
                KnowledgePoint.frequency > 0,
            )
            .order_by(KnowledgePoint.frequency.desc())
            .limit(limit * 2)
            .all()
        )

        # Filter to those not mastered
        mastery_map = {}
        if points:
            masteries = (
                self.db.query(UserMastery)
                .filter(
                    UserMastery.user_id == user_id,
                    UserMastery.knowledge_point_id.in_([p.id for p in points]),
                )
                .all()
            )
            mastery_map = {m.knowledge_point_id: m.mastery_level for m in masteries}

        result = []
        for p in points:
            mastery = mastery_map.get(p.id, 0.0)
            if mastery < 0.7:
                result.append({
                    "point_id": p.id,
                    "name": p.name,
                    "frequency": p.frequency,
                    "importance": p.importance,
                    "mastery_level": mastery,
                    "priority": "high" if mastery < 0.4 else "medium",
                })
            if len(result) >= limit:
                break

        return result

    def _analyze_type_weakness(
        self, user_id: int, subject_id: int
    ) -> List[Dict[str, Any]]:
        """Analyze score rate by question type from exam history."""
        sessions = (
            self.db.query(ExamSession)
            .join(ExamResult, ExamResult.session_id == ExamSession.session_id)
            .filter(
                ExamSession.user_id == user_id,
                ExamSession.status == ExamStatus.COMPLETED.value,
            )
            .order_by(ExamSession.submitted_at.desc())
            .limit(10)
            .all()
        )

        type_stats: Dict[str, Dict[str, int]] = {}
        for session in sessions:
            result = (
                self.db.query(ExamResult)
                .filter(ExamResult.session_id == session.session_id)
                .first()
            )
            if not result or not result.result:
                continue
            details = result.result.get("details", {})
            if isinstance(details, list):
                # Normalize - some results use list format
                details_iter = details
            else:
                details_iter = details.values()

            for detail in details_iter:
                qtype = detail.get("question_type", "unknown")
                if qtype not in type_stats:
                    type_stats[qtype] = {"total": 0, "correct": 0, "score": 0, "full_score": 0}
                type_stats[qtype]["total"] += 1
                if detail.get("is_correct"):
                    type_stats[qtype]["correct"] += 1
                type_stats[qtype]["score"] += detail.get("score", 0)
                type_stats[qtype]["full_score"] += detail.get("full_score", detail.get("score", 0))

        result_list = []
        type_labels = {
            "single_choice": "单选题",
            "multiple_choice": "多选题",
            "fill_blank": "填空题",
            "short_answer": "简答题",
            "essay": "论述题",
            "case": "案例题",
        }
        for qtype, stats in type_stats.items():
            accuracy = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
            score_rate = stats["score"] / stats["full_score"] if stats["full_score"] > 0 else 0
            result_list.append({
                "question_type": qtype,
                "label": type_labels.get(qtype, qtype),
                "total_count": stats["total"],
                "correct_count": stats["correct"],
                "accuracy": round(accuracy, 2),
                "score_rate": round(score_rate, 2),
            })

        # Sort by score_rate ascending (weakest first)
        result_list.sort(key=lambda x: x["score_rate"])
        return result_list

    def _get_recent_scores(
        self, user_id: int, subject_id: int, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get recent exam score history."""
        from backend.models.exam import Exam

        sessions = (
            self.db.query(ExamSession, Exam)
            .join(Exam, ExamSession.exam_id == Exam.id)
            .filter(
                ExamSession.user_id == user_id,
                ExamSession.status == ExamStatus.COMPLETED.value,
                Exam.subject_id == subject_id,
                ExamSession.score.isnot(None),
            )
            .order_by(ExamSession.submitted_at.desc())
            .limit(limit)
            .all()
        )

        result = []
        for session, exam in sessions:
            total = exam.total_score or 100
            score_rate = session.score / total if total > 0 else 0
            result.append({
                "session_id": session.session_id,
                "score": session.score,
                "total_score": total,
                "score_rate": round(score_rate, 2),
                "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
            })

        result.reverse()  # Chronological order
        return result

    def _get_unmastered_wrong_count(self, user_id: int, subject_id: int) -> int:
        """Count unmastered wrong questions for the subject."""
        return (
            self.db.query(WrongQuestion)
            .join(Question, WrongQuestion.question_id == Question.id)
            .filter(
                WrongQuestion.user_id == user_id,
                WrongQuestion.is_mastered.is_(False),
                Question.subject_id == subject_id,
            )
            .count()
        )

    @staticmethod
    def _estimate_pass_probability(avg_score_rate: float) -> Dict[str, Any]:
        """Estimate pass probability based on average score rate."""
        if avg_score_rate >= 0.75:
            return {"level": "high", "label": "高", "percent": 85, "description": "保持当前状态，通过概率很高"}
        if avg_score_rate >= 0.6:
            return {"level": "medium", "label": "中", "percent": 60, "description": "在及格线附近，需要巩固薄弱环节"}
        if avg_score_rate >= 0.45:
            return {"level": "low", "label": "有风险", "percent": 40, "description": "存在不及格风险，需集中突破"}
        return {"level": "critical", "label": "需加强", "percent": 20, "description": "距离及格线较远，建议重点攻克高频考点"}

    @staticmethod
    def _get_trend(score_history: List[Dict[str, Any]]) -> str:
        """Determine score trend direction."""
        if len(score_history) < 2:
            return "insufficient_data"
        recent = score_history[-3:] if len(score_history) >= 3 else score_history
        first_half = sum(s["score_rate"] for s in recent[: len(recent) // 2 + 1]) / (len(recent) // 2 + 1)
        second_half = sum(s["score_rate"] for s in recent[len(recent) // 2:]) / (len(recent) - len(recent) // 2)
        if second_half - first_half > 0.05:
            return "improving"
        if first_half - second_half > 0.05:
            return "declining"
        return "stable"

    @staticmethod
    def _build_pass_strategy(type_weakness: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Build minimum pass strategy (target 60 points)."""
        priority_order = [
            "选择题确保80%正确率（≈24分）",
            "填空题确保60%正确率（≈9分）",
            "简答题每题写满3-4个要点（≈18分）",
            "论述题按模板写300字以上（≈9分）",
        ]

        # Add specific advice based on weakest types
        focus_advice = []
        for tw in type_weakness[:2]:
            if tw["score_rate"] < 0.5:
                focus_advice.append(
                    f"{tw['label']}得分率仅{int(tw['score_rate']*100)}%，是主要失分点，需重点突破"
                )

        return {
            "target_score": 60,
            "priority_order": priority_order,
            "focus_advice": focus_advice,
            "guaranteed_minimum": "选择题24分 + 填空题6分 + 简答题18分 + 论述题12分 = 60分",
        }

    @staticmethod
    def _build_time_allocation(
        days_remaining: int,
        type_weakness: List[Dict[str, Any]],
        unmastered_count: int,
    ) -> Dict[str, Any]:
        """Build time allocation recommendation."""
        if days_remaining <= 3:
            return {
                "strategy": "考前3天：只刷高频+错题",
                "details": "不学新内容，反复回顾已学知识点",
                "allocation": [
                    {"item": "高频考点回顾", "percent": 50},
                    {"item": "错题重做", "percent": 30},
                    {"item": "答题模板记忆", "percent": 20},
                ],
            }
        elif days_remaining <= 7:
            return {
                "strategy": "考前一周：5:3:2分配",
                "details": "50%刷高频考点 + 30%做错题 + 20%背答题模板",
                "allocation": [
                    {"item": "高频考点专项练习", "percent": 50},
                    {"item": "错题复习与重做", "percent": 30},
                    {"item": "答题模板与技巧", "percent": 20},
                ],
            }
        else:
            return {
                "strategy": "考前两周+：4:3:2:1分配",
                "details": "40%薄弱知识点 + 30%刷题 + 20%错题复习 + 10%模拟考试",
                "allocation": [
                    {"item": "薄弱知识点学习", "percent": 40},
                    {"item": "题库刷题练习", "percent": 30},
                    {"item": "错题复习", "percent": 20},
                    {"item": "全真模拟考试", "percent": 10},
                ],
            }
