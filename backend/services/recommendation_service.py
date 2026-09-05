# -*- coding: utf-8 -*-
"""Course recommendation service: suggest next courses to take based on user profile."""

from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.models.enrollment import Major, MajorSubject, UserEnrollment, UserSubjectStatus
from backend.models.subject import Subject
from backend.models.question import Question
from backend.models.user import User


# Course difficulty estimation by category
DIFFICULTY_MAP = {
    "public": 1,
    "language": 3,
    "computer": 3,
    "economics_management": 2,
    "law": 2,
    "education": 2,
    "design": 2,
    "engineering": 3,
    "medicine": 3,
    "public_security": 2,
    "professional": 2,
}

# Credits-to-study-hours rough ratio
CREDITS_TO_HOURS = 15  # 1 credit ~ 15 hours of study


class CourseRecommendationService:
    def __init__(self, db: Session):
        self.db = db

    def get_recommendation(
        self,
        user_id: int,
        enrollment_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate course recommendation based on user profile and enrollment status."""
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            raise ValueError("用户不存在")

        # Load enrollments
        enrollment_query = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.user_id == user_id, UserEnrollment.is_active.is_(True))
        )
        if enrollment_id:
            enrollment_query = enrollment_query.filter(UserEnrollment.id == enrollment_id)
        enrollments = enrollment_query.all()

        if not enrollments:
            return {
                "user_profile": self._serialize_profile(user),
                "recommendations": [],
                "study_plan": None,
                "sprint_plan": None,
                "message": "请先添加报考专业",
            }

        # Gather all subjects across enrollments
        all_subjects = []  # (subject, major_subject, status, enrollment)
        passed_codes = set()
        remaining_subjects = []

        for enrollment in enrollments:
            rows = (
                self.db.query(MajorSubject, Subject, UserSubjectStatus)
                .join(Subject, MajorSubject.subject_id == Subject.id)
                .outerjoin(
                    UserSubjectStatus,
                    (UserSubjectStatus.subject_id == MajorSubject.subject_id)
                    & (UserSubjectStatus.enrollment_id == enrollment.id)
                    & (UserSubjectStatus.user_id == user_id),
                )
                .filter(MajorSubject.major_id == enrollment.major_id)
                .order_by(MajorSubject.sort_order.asc())
                .all()
            )
            for ms, subj, status in rows:
                st = status.status if status else "not_taken"
                if st == "passed":
                    passed_codes.add(subj.code)
                else:
                    remaining_subjects.append({
                        "subject": subj,
                        "major_subject": ms,
                        "status": st,
                        "enrollment_id": enrollment.id,
                    })

        # Deduplicate remaining by code
        seen_codes = set()
        unique_remaining = []
        for r in remaining_subjects:
            code = r["subject"].code
            if code not in seen_codes and code not in passed_codes:
                seen_codes.add(code)
                unique_remaining.append(r)

        # Score and rank each remaining subject
        scored = []
        for r in unique_remaining:
            subj = r["subject"]
            ms = r["major_subject"]
            score = self._score_subject(user, subj, ms, passed_codes)
            scored.append({**r, "priority_score": score})

        scored.sort(key=lambda x: x["priority_score"], reverse=True)

        # Build recommendations
        recommendations = []
        for item in scored:
            subj = item["subject"]
            ms = item["major_subject"]
            q_count = self.db.query(func.count(Question.id)).filter(Question.subject_id == subj.id).scalar() or 0
            recommendations.append({
                "code": subj.code,
                "name": subj.name,
                "credits": ms.credits,
                "course_type": ms.course_type,
                "category": subj.category,
                "status": item["status"],
                "priority_score": round(item["priority_score"], 1),
                "question_count": q_count,
                "reason": self._explain_reason(user, subj, ms, item["priority_score"]),
                "estimated_hours": int((ms.credits or 3) * CREDITS_TO_HOURS),
            })

        # Generate study plan
        study_plan = self._generate_study_plan(user, recommendations)

        # Generate sprint plan (for next exam session)
        sprint_plan = self._generate_sprint_plan(user, recommendations)

        return {
            "user_profile": self._serialize_profile(user),
            "total_remaining": len(unique_remaining),
            "total_passed": len(passed_codes),
            "recommendations": recommendations[:20],  # Top 20
            "next_exam_picks": recommendations[:4],  # Top 4 for next session
            "study_plan": study_plan,
            "sprint_plan": sprint_plan,
        }

    def _score_subject(
        self, user: User, subj: Subject, ms: MajorSubject, passed_codes: set
    ) -> float:
        """Score a subject for priority (higher = should take sooner)."""
        score = 50.0  # base

        # 1. Public/required courses first
        if ms.course_type == "required":
            score += 20
        elif ms.course_type == "elective":
            score += 5

        # 2. Public courses (easy, foundational)
        if subj.category == "public":
            score += 15

        # 3. Difficulty adjustment based on user experience
        cat_difficulty = DIFFICULTY_MAP.get(subj.category, 2)
        if user.exam_experience == "none" or user.exam_experience == "beginner":
            # Beginners should start with easier courses
            score += (4 - cat_difficulty) * 8
        else:
            # Experienced students can tackle harder ones
            score += cat_difficulty * 3

        # 4. Credits weight (higher credits = more important)
        credits = ms.credits or 3
        score += credits * 1.5

        # 5. Question availability (having questions = better for practice)
        q_count = self.db.query(func.count(Question.id)).filter(Question.subject_id == subj.id).scalar() or 0
        if q_count > 100:
            score += 10
        elif q_count > 30:
            score += 5
        elif q_count > 0:
            score += 2

        # 6. Skills match bonus
        if user.skills:
            skill_list = [s.strip().lower() for s in user.skills.split(",")]
            name_lower = subj.name.lower()
            for skill in skill_list:
                if skill and skill in name_lower:
                    score += 8
                    break

        # 7. Education background match
        if user.education_major:
            major_lower = user.education_major.lower()
            if any(kw in subj.name.lower() for kw in major_lower.split()):
                score += 5

        # 8. Failed subjects get slight priority (retry)
        # Already handled by status in remaining

        # 9. Practical courses should come after theory
        if "实践" in subj.name or "毕业" in subj.name:
            score -= 30  # Push to later

        return score

    def _explain_reason(self, user: User, subj: Subject, ms: MajorSubject, score: float) -> str:
        """Generate human-readable reason for recommendation."""
        reasons = []
        if ms.course_type == "required":
            reasons.append("必考课，优先安排")
        if subj.category == "public":
            reasons.append("公共课，通用性强")
        credits = ms.credits or 3
        if credits >= 6:
            reasons.append("高学分(%d分)，性价比高" % credits)

        cat_difficulty = DIFFICULTY_MAP.get(subj.category, 2)
        if cat_difficulty == 1:
            reasons.append("难度较低，适合先考")
        elif cat_difficulty >= 3:
            reasons.append("难度较高，建议集中备考")

        q_count = self.db.query(func.count(Question.id)).filter(Question.subject_id == subj.id).scalar() or 0
        if q_count > 50:
            reasons.append("题库丰富(%d题)，便于刷题" % q_count)
        elif q_count == 0:
            reasons.append("暂无题库，建议以教材为主")

        if user.skills:
            skill_list = [s.strip().lower() for s in user.skills.split(",")]
            for skill in skill_list:
                if skill and skill in subj.name.lower():
                    reasons.append("与你的技能'%s'相关" % skill)
                    break

        if "实践" in subj.name:
            reasons.append("实践课，需先通过对应理论课")

        return "；".join(reasons) if reasons else "常规课程"

    def _generate_study_plan(
        self, user: User, recommendations: List[Dict],
    ) -> Dict[str, Any]:
        """Generate a study plan based on remaining courses."""
        daily_hours = user.study_hours_per_day or 3
        remaining = [r for r in recommendations if "实践" not in r["name"] and "毕业" not in r["name"]]

        if not remaining:
            return {"message": "所有理论课已通过！", "phases": []}

        # Split into phases (4 courses per exam session)
        phases = []
        for i in range(0, len(remaining), 4):
            batch = remaining[i:i + 4]
            total_hours = sum(r["estimated_hours"] for r in batch)
            weeks_needed = max(4, total_hours // (daily_hours * 7) + 1)
            phases.append({
                "phase": len(phases) + 1,
                "courses": [
                    {"code": r["code"], "name": r["name"], "credits": r["credits"], "hours": r["estimated_hours"]}
                    for r in batch
                ],
                "total_hours": total_hours,
                "weeks_needed": weeks_needed,
                "daily_hours": daily_hours,
                "strategy": self._phase_strategy(batch, daily_hours),
            })

        return {
            "total_courses": len(remaining),
            "total_phases": len(phases),
            "daily_hours": daily_hours,
            "phases": phases,
        }

    def _phase_strategy(self, batch: List[Dict], daily_hours: int) -> str:
        """Generate study strategy for a phase."""
        if len(batch) <= 2:
            return "科目较少，建议每天交替学习两门，每门%d小时。" % max(1, daily_hours // 2)
        if daily_hours >= 4:
            return "建议上午学理论课（2小时），下午刷题练习（2小时），晚上复习回顾。"
        if daily_hours >= 2:
            return "时间有限，建议工作日每天专注一门课，周末集中刷题和模拟。"
        return "每天学习时间不多，建议利用碎片时间刷题，周末集中看教材。"

    def _generate_sprint_plan(
        self, user: User, recommendations: List[Dict],
    ) -> Dict[str, Any]:
        """Generate a sprint plan for the next exam session (top 4 courses)."""
        daily_hours = user.study_hours_per_day or 3
        picks = [r for r in recommendations[:4] if "实践" not in r["name"] and "毕业" not in r["name"]]

        if not picks:
            return {"message": "暂无需要冲刺的课程", "weeks": []}

        total_hours = sum(r["estimated_hours"] for r in picks)
        available_weeks = 8  # Assume 8 weeks sprint

        weeks = []
        # Phase 1: Foundation (weeks 1-3)
        weeks.append({
            "period": "第1-3周：基础阶段",
            "focus": "通读教材，理解核心概念",
            "tasks": [
                "每天学习%d小时，按课程轮流推进" % daily_hours,
                "标记重点章节和难点",
                "完成每章课后习题",
            ],
            "courses": [{"code": r["code"], "name": r["name"]} for r in picks],
        })
        # Phase 2: Strengthen (weeks 4-5)
        weeks.append({
            "period": "第4-5周：强化阶段",
            "focus": "刷题+查漏补缺",
            "tasks": [
                "大量刷历年真题和模拟题",
                "整理错题本，分析错误原因",
                "重点攻克薄弱章节",
            ],
            "courses": [{"code": r["code"], "name": r["name"]} for r in picks],
        })
        # Phase 3: Sprint (weeks 6-8)
        weeks.append({
            "period": "第6-8周：冲刺阶段",
            "focus": "模拟考试+重点记忆",
            "tasks": [
                "每周至少完成2套模拟试卷",
                "背诵简答题和论述题答题模板",
                "回顾错题本和高频考点",
                "考前3天重点复习公式/法条/时间线",
            ],
            "courses": [{"code": r["code"], "name": r["name"]} for r in picks],
        })

        return {
            "course_count": len(picks),
            "total_hours": total_hours,
            "sprint_weeks": available_weeks,
            "daily_hours": daily_hours,
            "picks": [{"code": r["code"], "name": r["name"], "credits": r["credits"], "reason": r["reason"]} for r in picks],
            "weeks": weeks,
            "tips": [
                "公共课和专业课搭配报考，避免同一考期全选难科",
                "实践课需对应理论课通过后方可报考",
                "考前一周以回顾为主，不要学习新内容",
                "保持规律作息，考试当天提前到达考场",
            ],
        }

    def _serialize_profile(self, user: User) -> Dict[str, Any]:
        return {
            "full_name": user.full_name,
            "current_job": user.current_job,
            "education_background": user.education_background,
            "education_major": user.education_major,
            "skills": user.skills,
            "study_hours_per_day": user.study_hours_per_day,
            "exam_experience": user.exam_experience,
            "learning_preference": user.learning_preference,
        }
