# -*- coding: utf-8 -*-
"""Enrollment service: major lookup, enrollment management, subject status tracking."""

from datetime import date
from typing import Any, Dict, List, Optional

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.enrollment import (
    Major,
    MajorSubject,
    Province,
    School,
    UserEnrollment,
    UserSubjectStatus,
)
from backend.models.subject import Subject
from backend.data.self_exam_catalog import LEGACY_COURSE_CODE_ALIASES

# 完整的新旧课程替代映射: 新代码 -> {old_code, old_name, note}
# 包括公共政治课 + 计算机科学与技术 + 法律事务的专业课替代
_REPLACEMENT_INFO: dict[str, dict] = {}

# 公共政治课替代
_PUBLIC_REPLACEMENTS = {
    "15042": {"old_code": "03706", "old_name": "思想道德修养与法律基础",
              "note": "2025年起 03706 停用，已通过可替代 15042，无需重考。"},
    "15043": {"old_code": "03708", "old_name": "中国近现代史纲要",
              "note": "2025年起 03708 停用，已通过可替代 15043，无需重考。"},
    "15044": {"old_code": "03709", "old_name": "马克思主义基本原理概论",
              "note": "2025年起 03709 停用，已通过可替代 15044，无需重考。"},
    "15041": {"old_code": "12656", "old_name": "毛泽东思想和中国特色社会主义理论体系概论",
              "note": "2025年起 12656 停用，已通过可替代 15041，无需重考。"},
}

# 计算机科学与技术(080901)专业课替代
_CS_REPLACEMENTS = {
    "13000": {"old_code": "00015", "old_name": "英语(二)",
              "note": "外语课程改革，14学分下调为7学分。已通过 00015 可替代。"},
    "00023": {"old_code": "00910", "old_name": "网络经济与企业管理",
              "note": "课程置换：偏文管调整为数学工科核心。已通过 00910 可替代。"},
    "02324": {"old_code": "02375", "old_name": "运筹学基础",
              "note": "课程置换：改为计算机核心基础。已通过 02375 可替代。"},
    "13013": {"old_code": "04737", "old_name": "C++程序设计",
              "note": "编程语言基础课调整（理论）。已通过 04737 可替代。"},
    "13014": {"old_code": "04738", "old_name": "C++程序设计(实践)",
              "note": "编程语言基础课调整（实践）。已通过 04738 可替代。"},
    "13003": {"old_code": "04735", "old_name": "数据库系统原理",
              "note": "核心课对应调整（理论）。已通过 04735 可替代。"},
    "13004": {"old_code": "04736", "old_name": "数据库系统原理(实践)",
              "note": "核心课对应调整（实践）。已通过 04736 可替代。"},
    "13015": {"old_code": "04741", "old_name": "计算机网络原理",
              "note": "课程置换。已通过 04741 可替代。"},
    "13180": {"old_code": "02323", "old_name": "操作系统概论",
              "note": "课程代码及大纲更新。已通过 02323 可替代。"},
    "14263": {"old_code": "02142", "old_name": "数据结构导论",
              "note": "课程置换（硬件基础）。已通过 02142 可替代。"},
    "13009": {"old_code": "02378", "old_name": "信息资源管理",
              "note": "课程置换（原数据库合并调整）。已通过 02378 可替代。"},
    "13005": {"old_code": "04757", "old_name": "信息系统开发与管理",
              "note": "课程置换。已通过 04757 可替代。"},
    "13017": {"old_code": "03173", "old_name": "软件开发工具",
              "note": "理论+实践合并顶替新课。已通过 03173 可替代。"},
    "14349": {"old_code": "02628", "old_name": "管理经济学",
              "note": "去除管理类，改为系统集成技术。已通过 02628 可替代。"},
}

# 法律事务(专科)专业课替代
_LAW_REPLACEMENTS = {
    "14005": {"old_code": "04729", "old_name": "大学语文",
              "note": "公共基础课调整为专业课。已通过 04729 可替代。"},
    "07790": {"old_code": "00244", "old_name": "经济法概论",
              "note": "课程代码及名称微调。已通过 00244 可替代。"},
    "00264": {"old_code": "00247", "old_name": "国际法",
              "note": "专业方向课程置换。已通过 00247 可替代。"},
}

# 特殊多对一替代
_SPECIAL_REPLACEMENTS = {
    "05680": {"old_code": "05680/00261", "old_name": "婚姻家庭法/行政法学",
              "note": "原 05680 或 00261 任一通过，均可顶替新计划 05680。"},
}

_REPLACEMENT_INFO.update(_PUBLIC_REPLACEMENTS)
_REPLACEMENT_INFO.update(_CS_REPLACEMENTS)
_REPLACEMENT_INFO.update(_LAW_REPLACEMENTS)
_REPLACEMENT_INFO.update(_SPECIAL_REPLACEMENTS)


class EnrollmentService:
    def __init__(self, db: Session):
        self.db = db

    # ------------------------------------------------------------------
    # Province / School / Major queries
    # ------------------------------------------------------------------

    def list_provinces(self) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(Province)
            .filter(Province.is_active.is_(True))
            .order_by(Province.code.asc())
            .all()
        )
        return [{"id": r.id, "code": r.code, "name": r.name} for r in rows]

    def list_schools(self, province_id: Optional[int] = None) -> List[Dict[str, Any]]:
        query = self.db.query(School).filter(School.is_active.is_(True))
        if province_id:
            query = query.filter(School.province_id == province_id)
        rows = query.order_by(School.name.asc()).all()
        return [
            {"id": r.id, "name": r.name, "province_id": r.province_id, "code": r.code, "logo_url": r.logo_url}
            for r in rows
        ]

    def list_majors(
        self,
        province_id: Optional[int] = None,
        school_id: Optional[int] = None,
        level: Optional[str] = None,
        q: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.query(Major).filter(Major.is_active.is_(True))
        if province_id:
            query = query.filter(Major.province_id == province_id)
        if school_id:
            query = query.filter(Major.school_id == school_id)
        if level:
            query = query.filter(Major.level == level)
        if q:
            pattern = f"%{q.strip()}%"
            query = query.filter((Major.code.ilike(pattern)) | (Major.name.ilike(pattern)))
        rows = query.order_by(Major.code.asc()).all()
        return [
            {
                "id": r.id,
                "code": r.code,
                "name": r.name,
                "level": r.level,
                "province_id": r.province_id,
                "school_id": r.school_id,
                "total_credits": r.total_credits,
                "description": r.description,
            }
            for r in rows
        ]

    def get_major_subjects(self, major_id: int) -> List[Dict[str, Any]]:
        """获取某专业的全部考试科目计划"""
        rows = (
            self.db.query(MajorSubject, Subject)
            .join(Subject, MajorSubject.subject_id == Subject.id)
            .filter(MajorSubject.major_id == major_id)
            .order_by(MajorSubject.sort_order.asc(), MajorSubject.id.asc())
            .all()
        )
        return [
            {
                "subject_id": ms.subject_id,
                "code": subj.code,
                "name": subj.name,
                "course_type": ms.course_type,
                "credits": ms.credits,
                "sort_order": ms.sort_order,
            }
            for ms, subj in rows
        ]

    # ------------------------------------------------------------------
    # User Enrollment
    # ------------------------------------------------------------------

    def create_enrollment(
        self, user_id: int, major_id: int, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        # 验证专业存在
        major = self.db.query(Major).filter(Major.id == major_id, Major.is_active.is_(True)).first()
        if not major:
            raise ValueError("专业不存在或已下线")

        # 检查重复
        existing = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.user_id == user_id, UserEnrollment.major_id == major_id)
            .first()
        )
        if existing:
            if not existing.is_active:
                existing.is_active = True
                existing.target_date = target_date
                self.db.commit()
                self.db.refresh(existing)
                # 重新激活时同步补充可能新增的科目状态
                self._init_subject_status(user_id, existing.id, major_id)
                return self._enrollment_to_dict(existing)
            raise ValueError("已经报考了该专业")

        enrollment = UserEnrollment(
            user_id=user_id,
            major_id=major_id,
            target_date=target_date,
            is_active=True,
        )
        self.db.add(enrollment)
        self.db.commit()
        self.db.refresh(enrollment)

        # 自动为该专业所有科目创建初始状态
        self._init_subject_status(user_id, enrollment.id, major_id)

        return self._enrollment_to_dict(enrollment)

    def _init_subject_status(self, user_id: int, enrollment_id: int, major_id: int) -> None:
        """为新报考初始化所有科目状态为 not_taken"""
        major_subjects = (
            self.db.query(MajorSubject)
            .filter(MajorSubject.major_id == major_id)
            .all()
        )
        for ms in major_subjects:
            existing = (
                self.db.query(UserSubjectStatus)
                .filter(
                    UserSubjectStatus.user_id == user_id,
                    UserSubjectStatus.subject_id == ms.subject_id,
                    UserSubjectStatus.enrollment_id == enrollment_id,
                )
                .first()
            )
            if not existing:
                self.db.add(UserSubjectStatus(
                    user_id=user_id,
                    subject_id=ms.subject_id,
                    enrollment_id=enrollment_id,
                    status="not_taken",
                ))
        self.db.commit()

    def list_enrollments(self, user_id: int) -> List[Dict[str, Any]]:
        rows = (
            self.db.query(UserEnrollment, Major, School, Province)
            .join(Major, UserEnrollment.major_id == Major.id)
            .join(School, Major.school_id == School.id)
            .join(Province, Major.province_id == Province.id)
            .filter(UserEnrollment.user_id == user_id, UserEnrollment.is_active.is_(True))
            .order_by(UserEnrollment.created_at.desc())
            .all()
        )
        results = []
        for enrollment, major, school, province in rows:
            progress = self._calc_progress(enrollment.id)
            results.append({
                "id": enrollment.id,
                "major_id": major.id,
                "major_code": major.code,
                "major_name": major.name,
                "level": major.level,
                "school_name": school.name,
                "province_name": province.name,
                "target_date": enrollment.target_date.isoformat() if enrollment.target_date else None,
                "is_active": enrollment.is_active,
                "created_at": enrollment.created_at.isoformat() if enrollment.created_at else None,
                "progress": progress,
            })
        return results

    def delete_enrollment(self, user_id: int, enrollment_id: int) -> None:
        enrollment = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.id == enrollment_id, UserEnrollment.user_id == user_id)
            .first()
        )
        if not enrollment:
            raise ValueError("报考记录不存在")
        enrollment.is_active = False
        self.db.commit()

    def update_enrollment(
        self, user_id: int, enrollment_id: int, target_date: Optional[date] = None
    ) -> Dict[str, Any]:
        enrollment = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.id == enrollment_id, UserEnrollment.user_id == user_id)
            .first()
        )
        if not enrollment:
            raise ValueError("报考记录不存在")
        enrollment.target_date = target_date
        self.db.commit()
        self.db.refresh(enrollment)
        return self._enrollment_to_dict(enrollment)

    # ------------------------------------------------------------------
    # Enrollment Subjects with Status
    # ------------------------------------------------------------------

    def get_enrollment_subjects(self, user_id: int, enrollment_id: int) -> Dict[str, Any]:
        """获取某次报考的全部科目及用户状态，按 course_type 分组"""
        enrollment = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.id == enrollment_id, UserEnrollment.user_id == user_id, UserEnrollment.is_active.is_(True))
            .first()
        )
        if not enrollment:
            raise ValueError("报考记录不存在")

        major = self.db.query(Major).filter(Major.id == enrollment.major_id).first()
        school = self.db.query(School).filter(School.id == major.school_id).first()
        province = self.db.query(Province).filter(Province.id == major.province_id).first()

        # 查询专业科目 + 科目详情 + 用户状态
        rows = (
            self.db.query(MajorSubject, Subject, UserSubjectStatus)
            .join(Subject, MajorSubject.subject_id == Subject.id)
            .outerjoin(
                UserSubjectStatus,
                (UserSubjectStatus.subject_id == MajorSubject.subject_id)
                & (UserSubjectStatus.enrollment_id == enrollment_id)
                & (UserSubjectStatus.user_id == user_id),
            )
            .filter(MajorSubject.major_id == enrollment.major_id)
            .order_by(MajorSubject.sort_order.asc(), MajorSubject.id.asc())
            .all()
        )

        # 分组
        grouped: Dict[str, List[Dict[str, Any]]] = {"required": [], "elective": [], "additional": []}
        for ms, subj, user_status in rows:
            item = {
                "subject_id": subj.id,
                "code": subj.code,
                "name": subj.name,
                "credits": ms.credits,
                "course_type": ms.course_type,
                "status": user_status.status if user_status else "not_taken",
                "score": user_status.score if user_status else None,
                "exam_date": user_status.exam_date.isoformat() if user_status and user_status.exam_date else None,
                "attempt_count": user_status.attempt_count if user_status else 0,
                "certificate_no": user_status.certificate_no if user_status else None,
                "note": user_status.note if user_status else None,
                # 课程替代信息
                "replaced_from_code": None,
                "replaced_from_name": None,
                "replacement_note": None,
            }
            # 如果是新代码且有对应旧代码, 附上替代说明
            rinfo = _REPLACEMENT_INFO.get(subj.code)
            if rinfo:
                item["replaced_from_code"] = rinfo["old_code"]
                item["replaced_from_name"] = rinfo["old_name"]
                item["replacement_note"] = rinfo["note"]
            group_key = ms.course_type if ms.course_type in grouped else "required"
            grouped[group_key].append(item)

        progress = self._calc_progress(enrollment_id)

        return {
            "enrollment": {
                "id": enrollment.id,
                "major_name": f"{major.name}({'本科' if major.level == 'bk' else '专科'})",
                "school_name": school.name if school else "",
                "province_name": province.name if province else "",
                "target_date": enrollment.target_date.isoformat() if enrollment.target_date else None,
            },
            "progress": progress,
            "subjects": grouped,
        }

    # ------------------------------------------------------------------
    # Subject Status Update
    # ------------------------------------------------------------------

    def update_subject_status(
        self,
        user_id: int,
        enrollment_id: int,
        subject_id: int,
        status: str,
        score: Optional[float] = None,
        exam_date: Optional[date] = None,
        certificate_no: Optional[str] = None,
        note: Optional[str] = None,
    ) -> Dict[str, Any]:
        if status not in ("not_taken", "passed", "failed"):
            raise ValueError("状态值无效，可选: not_taken, passed, failed")

        # 校验分数范围
        if score is not None and (score < 0 or score > 100):
            raise ValueError("分数范围应为 0-100")

        # 验证 enrollment 属于该用户
        enrollment = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.id == enrollment_id, UserEnrollment.user_id == user_id)
            .first()
        )
        if not enrollment:
            raise ValueError("报考记录不存在")

        user_status = (
            self.db.query(UserSubjectStatus)
            .filter(
                UserSubjectStatus.user_id == user_id,
                UserSubjectStatus.subject_id == subject_id,
                UserSubjectStatus.enrollment_id == enrollment_id,
            )
            .first()
        )

        if not user_status:
            user_status = UserSubjectStatus(
                user_id=user_id,
                subject_id=subject_id,
                enrollment_id=enrollment_id,
            )
            self.db.add(user_status)

        old_status = user_status.status
        user_status.status = status
        user_status.score = score
        user_status.exam_date = exam_date
        user_status.certificate_no = certificate_no
        if note is not None:
            user_status.note = note

        # 自动推导状态：有分数时根据分数判断
        if score is not None and status == "not_taken":
            user_status.status = "passed" if score >= 60 else "failed"

        # 更新考试次数：仅在状态从 not_taken 变为 passed/failed 时递增
        if old_status == "not_taken" and user_status.status in ("passed", "failed"):
            user_status.attempt_count = (user_status.attempt_count or 0) + 1

        self.db.commit()
        self.db.refresh(user_status)

        return {
            "subject_id": user_status.subject_id,
            "status": user_status.status,
            "score": user_status.score,
            "exam_date": user_status.exam_date.isoformat() if user_status.exam_date else None,
            "attempt_count": user_status.attempt_count,
        }

    # ------------------------------------------------------------------
    # Progress
    # ------------------------------------------------------------------

    def get_progress(self, user_id: int, enrollment_id: int) -> Dict[str, Any]:
        enrollment = (
            self.db.query(UserEnrollment)
            .filter(UserEnrollment.id == enrollment_id, UserEnrollment.user_id == user_id)
            .first()
        )
        if not enrollment:
            raise ValueError("报考记录不存在")
        return self._calc_progress(enrollment_id)

    def get_remaining_subjects(self, user_id: int, enrollment_id: int) -> List[int]:
        """获取用户剩余未通过的科目 ID 列表（供 planner 使用）"""
        rows = (
            self.db.query(UserSubjectStatus.subject_id)
            .filter(
                UserSubjectStatus.enrollment_id == enrollment_id,
                UserSubjectStatus.user_id == user_id,
                UserSubjectStatus.status != "passed",
            )
            .all()
        )
        return [r[0] for r in rows]

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _calc_progress(self, enrollment_id: int) -> Dict[str, Any]:
        """计算毕业进度"""
        rows = (
            self.db.query(UserSubjectStatus, MajorSubject)
            .join(
                MajorSubject,
                (MajorSubject.subject_id == UserSubjectStatus.subject_id)
                & (MajorSubject.major_id == self.db.query(UserEnrollment.major_id).filter(UserEnrollment.id == enrollment_id).scalar_subquery()),
            )
            .filter(UserSubjectStatus.enrollment_id == enrollment_id)
            .all()
        )

        total = len(rows)
        passed = 0
        failed = 0
        not_taken = 0
        total_credits = 0.0
        earned_credits = 0.0

        for status_row, ms in rows:
            credits = ms.credits or 0
            total_credits += credits
            if status_row.status == "passed":
                passed += 1
                earned_credits += credits
            elif status_row.status == "failed":
                failed += 1
            else:
                not_taken += 1

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "not_taken": not_taken,
            "total_credits": total_credits,
            "earned_credits": earned_credits,
            "completion_rate": round(passed / total, 3) if total > 0 else 0.0,
        }

    def _enrollment_to_dict(self, enrollment: UserEnrollment) -> Dict[str, Any]:
        return {
            "id": enrollment.id,
            "user_id": enrollment.user_id,
            "major_id": enrollment.major_id,
            "target_date": enrollment.target_date.isoformat() if enrollment.target_date else None,
            "is_active": enrollment.is_active,
            "created_at": enrollment.created_at.isoformat() if enrollment.created_at else None,
        }
