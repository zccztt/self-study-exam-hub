# -*- coding: utf-8 -*-
"""Exam calendar API: exam schedule from DB + fallback, countdown, registration reminders."""

from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models.exam_schedule import ExamSchedule

router = APIRouter(prefix="/exam-calendar", tags=["exam-calendar"])

# 每次考试最多报4科的建议
SUGGESTED_SUBJECTS_PER_SESSION = 4

# 静态兜底 (DB 为空时使用)
_FALLBACK = [
    {"period": "2025年4月", "reg_s": "2025-01-05", "reg_e": "2025-01-10", "ex_s": "2025-04-12", "ex_e": "2025-04-13", "result": "2025-05-20"},
    {"period": "2025年10月", "reg_s": "2025-06-10", "reg_e": "2025-06-15", "ex_s": "2025-10-25", "ex_e": "2025-10-26", "result": "2025-11-20"},
    {"period": "2026年4月", "reg_s": "2026-01-05", "reg_e": "2026-01-10", "ex_s": "2026-04-11", "ex_e": "2026-04-12", "result": "2026-05-20"},
    {"period": "2026年10月", "reg_s": "2026-06-10", "reg_e": "2026-06-15", "ex_s": "2026-10-24", "ex_e": "2026-10-25", "result": "2026-11-20"},
    {"period": "2027年4月", "reg_s": "2027-01-05", "reg_e": "2027-01-10", "ex_s": "2027-04-10", "ex_e": "2027-04-11", "result": "2027-05-20"},
    {"period": "2027年10月", "reg_s": "2027-06-10", "reg_e": "2027-06-15", "ex_s": "2027-10-23", "ex_e": "2027-10-24", "result": "2027-11-20"},
]


def _d(s: str) -> date:
    return datetime.strptime(s, "%Y-%m-%d").date()


def _load_schedules(db: Session) -> list[dict]:
    """Load exam schedules from DB, fallback to static data."""
    rows = db.query(ExamSchedule).order_by(ExamSchedule.exam_start.asc()).all()
    if rows:
        return [
            {
                "exam_period": r.exam_period,
                "register_start": r.register_start,
                "register_end": r.register_end,
                "exam_start": r.exam_start,
                "exam_end": r.exam_end,
                "result_date": r.result_date,
                "note": r.note or "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
                "source_url": r.source_url,
            }
            for r in rows
        ]
    # Fallback
    return [
        {
            "exam_period": f["period"],
            "register_start": _d(f["reg_s"]),
            "register_end": _d(f["reg_e"]),
            "exam_start": _d(f["ex_s"]),
            "exam_end": _d(f["ex_e"]),
            "result_date": _d(f["result"]),
            "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
            "source_url": None,
        }
        for f in _FALLBACK
    ]


def _days_between(d1: date, d2: date) -> int:
    return (d1 - d2).days


def _urgency(days: int) -> str:
    """Return urgency level for frontend highlighting."""
    if days <= 0:
        return "today"
    if days <= 7:
        return "critical"   # 红色高亮
    if days <= 30:
        return "warning"    # 橙色
    if days <= 60:
        return "attention"  # 黄色
    return "normal"


@router.get("/schedule")
async def get_exam_schedule(db: Session = Depends(get_db)):
    """获取全部考试时间安排"""
    schedules = _load_schedules(db)
    today = date.today()
    data = []
    for s in schedules:
        exam_start = s["exam_start"]
        days = _days_between(exam_start, today)
        data.append({
            "exam_period": s["exam_period"],
            "register_start": s["register_start"].isoformat() if s["register_start"] else None,
            "register_end": s["register_end"].isoformat() if s["register_end"] else None,
            "exam_start": exam_start.isoformat(),
            "exam_end": s["exam_end"].isoformat() if s["exam_end"] else None,
            "result_date": s["result_date"].isoformat() if s["result_date"] else None,
            "note": s["note"],
            "source_url": s.get("source_url"),
            "days_until_exam": days,
            "urgency": _urgency(days),
            "is_past": days < 0,
        })
    return {"code": 0, "data": data}


@router.get("/upcoming")
async def get_upcoming_events(db: Session = Depends(get_db)):
    """获取即将到来的考试及报名时间节点 + 倒计时 + 紧急程度"""
    schedules = _load_schedules(db)
    today = date.today()
    events = []

    for s in schedules:
        exam_start = s["exam_start"]
        exam_end = s["exam_end"] or exam_start
        reg_start = s["register_start"]
        reg_end = s["register_end"]
        result_date = s["result_date"]

        # --- 考试倒计时 ---
        exam_days = _days_between(exam_start, today)
        if exam_days >= -1:  # 包括今天和明天
            events.append({
                "type": "exam",
                "name": s["exam_period"] + " 考试",
                "countdown": {
                    "date": exam_start.isoformat(),
                    "days_remaining": exam_days,
                    "status": "today" if exam_days == 0 else "upcoming" if exam_days > 0 else "passed",
                },
                "dates": [exam_start.isoformat(), exam_end.isoformat()],
                "note": s["note"],
                "urgency": _urgency(exam_days),
                "highlight": exam_days <= 30,  # 30天内高亮
            })

        # --- 报名倒计时 ---
        if reg_start and reg_end:
            reg_days_start = _days_between(reg_start, today)
            reg_days_end = _days_between(reg_end, today)
            if reg_days_end >= 0:
                is_open = reg_days_start <= 0 <= reg_days_end
                events.append({
                    "type": "registration",
                    "name": s["exam_period"] + " 报名",
                    "countdown": {
                        "date": (reg_start if reg_days_start > 0 else reg_end).isoformat(),
                        "days_remaining": reg_days_start if reg_days_start > 0 else reg_days_end,
                        "status": "open" if is_open else "upcoming",
                    },
                    "register_start": reg_start.isoformat(),
                    "register_end": reg_end.isoformat(),
                    "status": "open" if is_open else "upcoming",
                    "urgency": "critical" if is_open else _urgency(reg_days_start),
                    "highlight": is_open or reg_days_start <= 14,
                })

        # --- 成绩查询倒计时 ---
        if result_date and exam_days < 0:
            result_days = _days_between(result_date, today)
            if result_days >= 0:
                events.append({
                    "type": "score",
                    "name": s["exam_period"] + " 成绩公布",
                    "countdown": {
                        "date": result_date.isoformat(),
                        "days_remaining": result_days,
                        "status": "today" if result_days == 0 else "upcoming",
                    },
                    "urgency": _urgency(result_days),
                    "highlight": result_days <= 7,
                })

    events.sort(key=lambda e: e["countdown"]["days_remaining"])
    return {"code": 0, "data": events, "source": "https://zk.hebeea.edu.cn/"}


@router.get("/study-plan-suggestion")
async def get_study_plan_suggestion(
    remaining: int = Query(..., description="剩余科目数"),
    target_date: Optional[str] = Query(default=None, description="目标毕业时间 YYYY-MM"),
    db: Session = Depends(get_db),
):
    """根据剩余科目数和目标日期，给出报考建议"""
    schedules = _load_schedules(db)
    today = date.today()

    future_sessions = [
        s for s in schedules if s["exam_start"] > today
    ]

    target_dt = None
    if target_date:
        try:
            target_dt = datetime.strptime(target_date.strip()[:7], "%Y-%m").date()
        except ValueError:
            pass

    available = future_sessions
    if target_dt:
        available = [s for s in future_sessions if s["exam_start"] <= target_dt]

    total_capacity = len(available) * SUGGESTED_SUBJECTS_PER_SESSION
    sessions_needed = (remaining + SUGGESTED_SUBJECTS_PER_SESSION - 1) // SUGGESTED_SUBJECTS_PER_SESSION if remaining > 0 else 0

    plan = []
    left = remaining
    for s in available[:sessions_needed]:
        take = min(left, SUGGESTED_SUBJECTS_PER_SESSION)
        plan.append({
            "name": s["exam_period"],
            "exam_date": s["exam_start"].isoformat(),
            "register_start": s["register_start"].isoformat() if s["register_start"] else None,
            "register_end": s["register_end"].isoformat() if s["register_end"] else None,
            "suggested_count": take,
            "days_until": _days_between(s["exam_start"], today),
        })
        left -= take
        if left <= 0:
            break

    feasible = total_capacity >= remaining
    if target_dt:
        advice = (
            "按每次考4科的节奏，您可以在目标时间内完成全部科目。建议优先安排公共课和难度较高的科目。"
            if feasible
            else "当前剩余科目较多，目标时间内可能无法全部考完（可用考期容量%d科 < 剩余%d科）。建议适当调整目标或增加每次报考科目数。" % (total_capacity, remaining)
        )
    else:
        advice = "预计需要 %d 个考期完成剩余 %d 门科目（每次报考4科）。建议设置一个目标毕业时间来获取更精准的规划。" % (sessions_needed, remaining)

    return {
        "code": 0,
        "data": {
            "remaining_subjects": remaining,
            "target_date": target_date,
            "sessions_needed": sessions_needed,
            "total_capacity": total_capacity,
            "feasible": feasible,
            "advice": advice,
            "plan": plan,
        },
    }

