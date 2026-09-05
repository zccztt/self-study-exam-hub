# -*- coding: utf-8 -*-
"""Data importer: saves crawled data into the database.

Takes CrawlResult + parsed majors and upserts into
Province, School, Major, MajorSubject, Subject tables.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.enrollment import Major, MajorSubject, Province, School
from backend.models.subject import Subject

logger = logging.getLogger(__name__)

# Province code -> name mapping
PROVINCE_NAMES = {
    "11": "北京市", "12": "天津市", "13": "河北省", "14": "山西省", "15": "内蒙古自治区",
    "21": "辽宁省", "22": "吉林省", "23": "黑龙江省",
    "31": "上海市", "32": "江苏省", "33": "浙江省", "34": "安徽省",
    "35": "福建省", "36": "江西省", "37": "山东省",
    "41": "河南省", "42": "湖北省", "43": "湖南省",
    "44": "广东省", "45": "广西壮族自治区", "46": "海南省",
    "50": "重庆市", "51": "四川省", "52": "贵州省", "53": "云南省", "54": "西藏自治区",
    "61": "陕西省", "62": "甘肃省", "63": "青海省", "64": "宁夏回族自治区", "65": "新疆维吾尔自治区",
}


class DataImporter:
    """Imports crawled major/course data into the database."""

    def __init__(self, db: Session):
        self.db = db
        self._subject_cache: Dict[str, int] = {}  # code -> id
        self._school_cache: Dict[str, int] = {}   # (province_id, name) -> id
        self._province_cache: Dict[str, int] = {}  # code -> id

    def ensure_province(self, code: str) -> int:
        """Ensure province exists, return id."""
        if code in self._province_cache:
            return self._province_cache[code]

        province = self.db.query(Province).filter(Province.code == code).first()
        if not province:
            name = PROVINCE_NAMES.get(code, f"省份{code}")
            province = Province(code=code, name=name)
            self.db.add(province)
            self.db.flush()
            logger.info(f"  Created province: {name} (code={code})")

        self._province_cache[code] = province.id
        return province.id

    def ensure_school(self, name: str, province_id: int) -> int:
        """Ensure school exists, return id."""
        cache_key = f"{province_id}:{name}"
        if cache_key in self._school_cache:
            return self._school_cache[cache_key]

        school = self.db.query(School).filter(
            School.name == name, School.province_id == province_id
        ).first()
        if not school:
            school = School(name=name, province_id=province_id)
            self.db.add(school)
            self.db.flush()
            logger.debug(f"  Created school: {name}")

        self._school_cache[cache_key] = school.id
        return school.id

    def ensure_subject(self, code: str, name: str) -> int:
        """Ensure subject exists, return id."""
        if code in self._subject_cache:
            return self._subject_cache[code]

        subject = self.db.query(Subject).filter(Subject.code == code).first()
        if not subject:
            subject = Subject(code=code, name=name, category="public")
            self.db.add(subject)
            self.db.flush()
        elif subject.name.startswith("课程") or subject.name.startswith("未命名") or subject.name.startswith("Course "):
            # Update stale placeholder name with real name from crawl
            if name and not name.startswith("课程") and not name.startswith("未命名"):
                subject.name = name
                self.db.flush()

        self._subject_cache[code] = subject.id
        return subject.id

    def import_majors(
        self,
        province_code: str,
        majors_data: List[Dict[str, Any]],
    ) -> Dict[str, int]:
        """Import a list of majors with their courses.

        Args:
            province_code: 2-digit province code
            majors_data: List of major dicts with structure:
                {
                    "code": "120201K",
                    "name": "工商管理",
                    "level": "bk",
                    "school_name": "河北经贸大学",
                    "total_credits": 74,
                    "courses": [
                        {"code": "03708", "name": "中国近现代史纲要", "credits": 2, "course_type": "required", "sort_order": 1},
                        ...
                    ]
                }

        Returns:
            Dict with counts: {"majors_created", "majors_updated", "links_created", "subjects_created"}
        """
        province_id = self.ensure_province(province_code)
        stats = {"majors_created": 0, "majors_updated": 0, "links_created": 0, "subjects_created": 0}

        for m_data in majors_data:
            code = m_data.get("code", "").strip()
            name = m_data.get("name", "").strip()
            level = m_data.get("level", "bk")
            school_name = m_data.get("school_name", "未知院校").strip()
            total_credits = m_data.get("total_credits")
            courses = m_data.get("courses", [])

            if not name:
                continue

            # Ensure school
            school_id = self.ensure_school(school_name, province_id)

            # Find or create major
            query = self.db.query(Major).filter(
                Major.province_id == province_id,
                Major.school_id == school_id,
                Major.level == level,
            )
            # Match by code if available, otherwise by name
            if code:
                existing = query.filter(Major.code == code).first()
            else:
                existing = query.filter(Major.name == name).first()

            if existing:
                # Update if data changed
                updated = False
                if code and existing.code != code:
                    existing.code = code
                    updated = True
                if total_credits and existing.total_credits != total_credits:
                    existing.total_credits = total_credits
                    updated = True
                if updated:
                    stats["majors_updated"] += 1
                major_id = existing.id
            else:
                major_obj = Major(
                    code=code or f"UNKNOWN_{name}",
                    name=name,
                    level=level,
                    province_id=province_id,
                    school_id=school_id,
                    total_credits=total_credits,
                )
                self.db.add(major_obj)
                self.db.flush()
                major_id = major_obj.id
                stats["majors_created"] += 1

            # Import courses
            for c_data in courses:
                c_code = c_data.get("code", "").strip()
                c_name = c_data.get("name", "").strip()
                c_credits = c_data.get("credits")
                c_type = c_data.get("course_type", "required")
                c_order = c_data.get("sort_order", 0)

                if not c_code or not c_name:
                    continue

                # Ensure subject
                subject_id = self.ensure_subject(c_code, c_name)

                # Check if link exists
                existing_link = self.db.query(MajorSubject).filter(
                    MajorSubject.major_id == major_id,
                    MajorSubject.subject_id == subject_id,
                ).first()

                if not existing_link:
                    self.db.add(MajorSubject(
                        major_id=major_id,
                        subject_id=subject_id,
                        course_type=c_type,
                        credits=c_credits,
                        sort_order=c_order,
                    ))
                    stats["links_created"] += 1
                else:
                    # Update credits/type if different
                    if c_credits and existing_link.credits != c_credits:
                        existing_link.credits = c_credits
                    if c_type and existing_link.course_type != c_type:
                        existing_link.course_type = c_type

        self.db.commit()
        return stats
