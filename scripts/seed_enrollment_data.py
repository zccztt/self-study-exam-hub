# -*- coding: utf-8 -*-
"""Seed script: import sample province, school, major, and exam plan data.

Usage:
    python -m scripts.seed_enrollment_data

This imports a small sample dataset for demonstration. For production, expand
with full data from provincial exam authority websites.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.enrollment import Major, MajorSubject, Province, School
from backend.models.subject import Subject


# ------------------------------------------------------------------
# Sample data
# ------------------------------------------------------------------

PROVINCES = [
    {"code": "44", "name": "广东省"},
    {"code": "33", "name": "浙江省"},
    {"code": "32", "name": "江苏省"},
    {"code": "11", "name": "北京市"},
    {"code": "31", "name": "上海市"},
    {"code": "43", "name": "湖南省"},
    {"code": "42", "name": "湖北省"},
    {"code": "51", "name": "四川省"},
]

SCHOOLS = [
    # 广东
    {"name": "华南师范大学", "province_code": "44", "code": "10574"},
    {"name": "暨南大学", "province_code": "44", "code": "10559"},
    {"name": "华南理工大学", "province_code": "44", "code": "10561"},
    {"name": "广东外语外贸大学", "province_code": "44", "code": "10034"},
    {"name": "深圳大学", "province_code": "44", "code": "10590"},
    # 浙江
    {"name": "浙江大学", "province_code": "33", "code": "10335"},
    {"name": "浙江工商大学", "province_code": "33", "code": "10353"},
    # 江苏
    {"name": "南京大学", "province_code": "32", "code": "10284"},
    {"name": "南京财经大学", "province_code": "32", "code": "10327"},
]

# Majors with their exam plans.
# subject_code references existing subjects in the `subjects` table.
MAJORS = [
    {
        "code": "120201K",
        "name": "工商管理",
        "level": "bk",
        "province_code": "44",
        "school_name": "华南师范大学",
        "total_credits": 74,
        "subjects": [
            # (subject_code, course_type, credits, sort_order)
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00051", "required", 3, 4),
            ("00052", "required", 1, 5),
            ("00054", "required", 4, 6),
            ("00067", "required", 6, 7),
            ("00149", "required", 5, 8),
            ("00150", "required", 6, 9),
            ("00151", "required", 4, 10),
            ("00152", "required", 6, 11),
            ("00153", "required", 4, 12),
            ("00154", "required", 4, 13),
            ("00178", "elective", 4, 14),
            ("00183", "elective", 4, 15),
        ],
    },
    {
        "code": "050101",
        "name": "汉语言文学",
        "level": "bk",
        "province_code": "44",
        "school_name": "暨南大学",
        "total_credits": 69,
        "subjects": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00018", "required", 5, 4),
            ("00537", "required", 7, 5),
            ("00538", "required", 7, 6),
            ("00539", "required", 7, 7),
            ("00540", "required", 7, 8),
            ("00541", "required", 7, 9),
        ],
    },
    {
        "code": "120206",
        "name": "人力资源管理",
        "level": "bk",
        "province_code": "44",
        "school_name": "华南师范大学",
        "total_credits": 73,
        "subjects": [
            ("03708", "required", 2, 1),
            ("03709", "required", 4, 2),
            ("00015", "required", 14, 3),
            ("00051", "required", 3, 4),
            ("00054", "required", 4, 5),
            ("06090", "required", 6, 6),
            ("06091", "required", 6, 7),
            ("06093", "required", 6, 8),
        ],
    },
]


def seed() -> None:
    db = SessionLocal()
    try:
        # 1. Provinces
        province_map = {}  # code -> id
        for p in PROVINCES:
            existing = db.query(Province).filter(Province.code == p["code"]).first()
            if not existing:
                obj = Province(code=p["code"], name=p["name"])
                db.add(obj)
                db.flush()
                province_map[p["code"]] = obj.id
            else:
                province_map[p["code"]] = existing.id

        # 2. Schools
        school_map = {}  # (province_code, name) -> id
        for s in SCHOOLS:
            province_id = province_map[s["province_code"]]
            existing = db.query(School).filter(School.name == s["name"], School.province_id == province_id).first()
            if not existing:
                obj = School(name=s["name"], province_id=province_id, code=s.get("code"))
                db.add(obj)
                db.flush()
                school_map[(s["province_code"], s["name"])] = obj.id
            else:
                school_map[(s["province_code"], s["name"])] = existing.id

        # 3. Majors + MajorSubjects
        for m in MAJORS:
            province_id = province_map[m["province_code"]]
            school_id = school_map[(m["province_code"], m["school_name"])]

            existing_major = (
                db.query(Major)
                .filter(Major.code == m["code"], Major.province_id == province_id, Major.school_id == school_id)
                .first()
            )
            if existing_major:
                major_id = existing_major.id
            else:
                major_obj = Major(
                    code=m["code"],
                    name=m["name"],
                    level=m["level"],
                    province_id=province_id,
                    school_id=school_id,
                    total_credits=m.get("total_credits"),
                )
                db.add(major_obj)
                db.flush()
                major_id = major_obj.id

            # Link subjects
            for subj_code, course_type, credits, sort_order in m["subjects"]:
                subject = db.query(Subject).filter(Subject.code == subj_code).first()
                if not subject:
                    # Look up name from hebei data catalog if available
                    from scripts.seed_hebei_data import COURSE_CATALOG
                    cat_name = COURSE_CATALOG.get(subj_code, (f"未命名课程({subj_code})", 0))[0]
                    subject = Subject(code=subj_code, name=cat_name, category="public")
                    db.add(subject)
                    db.flush()

                existing_link = (
                    db.query(MajorSubject)
                    .filter(MajorSubject.major_id == major_id, MajorSubject.subject_id == subject.id)
                    .first()
                )
                if not existing_link:
                    db.add(MajorSubject(
                        major_id=major_id,
                        subject_id=subject.id,
                        course_type=course_type,
                        credits=credits,
                        sort_order=sort_order,
                    ))

        db.commit()
        print("✅ Enrollment seed data imported successfully.")
        print(f"   Provinces: {len(PROVINCES)}")
        print(f"   Schools:   {len(SCHOOLS)}")
        print(f"   Majors:    {len(MAJORS)}")

    except Exception as e:
        db.rollback()
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
