# -*- coding: utf-8 -*-
"""Seed script: import major data for multiple provinces.

Covers additional popular provinces beyond Hebei:
- 广东省 (code=44) - extended
- 浙江省 (code=33)
- 江苏省 (code=32)
- 湖南省 (code=43)
- 四川省 (code=51)

Usage:
    python -m scripts.seed_multi_province_data
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.enrollment import Major, MajorSubject, Province, School
from backend.models.subject import Subject


# ------------------------------------------------------------------
# Province + Schools + Majors data
# ------------------------------------------------------------------

DATA = {
    "33": {
        "province": "浙江省",
        "schools": [
            {"name": "浙江大学", "code": "10335"},
            {"name": "浙江工商大学", "code": "10353"},
            {"name": "浙江师范大学", "code": "10345"},
            {"name": "浙江财经大学", "code": "11482"},
            {"name": "宁波大学", "code": "11646"},
            {"name": "浙江工业大学", "code": "10337"},
        ],
        "majors": [
            {
                "code": "120201K", "name": "工商管理", "level": "bk",
                "school": "浙江工商大学", "total_credits": 74,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("04183", "required", 5, 4),
                    ("04184", "required", 4, 5), ("00054", "required", 6, 6),
                    ("00067", "required", 6, 7), ("00149", "required", 6, 8),
                    ("00150", "required", 6, 9), ("00151", "required", 6, 10),
                    ("00152", "required", 4, 11), ("00153", "required", 4, 12),
                    ("00154", "required", 4, 13),
                ],
            },
            {
                "code": "030101K", "name": "法学", "level": "bk",
                "school": "浙江大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00226", "required", 4, 4),
                    ("00227", "required", 4, 5), ("00228", "required", 4, 6),
                    ("00230", "required", 5, 7), ("00246", "required", 6, 8),
                    ("00249", "required", 4, 9), ("00262", "required", 3, 10),
                    ("00263", "required", 4, 11), ("00264", "required", 4, 12),
                ],
            },
            {
                "code": "050101", "name": "汉语言文学", "level": "bk",
                "school": "浙江师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00537", "required", 6, 4),
                    ("00538", "required", 7, 5), ("00539", "required", 7, 6),
                    ("00540", "required", 6, 7), ("00541", "required", 6, 8),
                    ("00321", "required", 5, 9),
                ],
            },
            {
                "code": "120203K", "name": "会计学", "level": "bk",
                "school": "浙江财经大学", "total_credits": 74,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("04183", "required", 5, 4),
                    ("04184", "required", 4, 5), ("00058", "required", 5, 6),
                    ("00150", "required", 6, 7), ("00155", "required", 8, 8),
                    ("00159", "required", 6, 9), ("00160", "required", 4, 10),
                    ("00161", "required", 5, 11), ("00162", "required", 5, 12),
                ],
            },
            {
                "code": "120206", "name": "人力资源管理", "level": "bk",
                "school": "宁波大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00054", "required", 6, 4),
                    ("06090", "required", 6, 5), ("06091", "required", 6, 6),
                    ("06093", "required", 6, 7), ("06088", "required", 9, 8),
                    ("06089", "required", 8, 9), ("00152", "required", 4, 10),
                ],
            },
            {
                "code": "080901", "name": "计算机科学与技术", "level": "bk",
                "school": "浙江工业大学", "total_credits": 73,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00023", "required", 10, 4),
                    ("02197", "required", 3, 5), ("02324", "required", 3, 6),
                    ("02326", "required", 5, 7), ("02331", "required", 3, 8),
                    ("04735", "required", 4, 9), ("04741", "required", 4, 10),
                    ("02333", "required", 3, 11),
                ],
            },
        ],
    },
    "43": {
        "province": "湖南省",
        "schools": [
            {"name": "湖南大学", "code": "10532"},
            {"name": "中南大学", "code": "10533"},
            {"name": "湖南师范大学", "code": "10542"},
            {"name": "湘潭大学", "code": "10530"},
            {"name": "长沙理工大学", "code": "10536"},
            {"name": "湖南农业大学", "code": "10537"},
        ],
        "majors": [
            {
                "code": "120201K", "name": "工商管理", "level": "bk",
                "school": "湖南大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00054", "required", 6, 4),
                    ("00067", "required", 6, 5), ("00149", "required", 6, 6),
                    ("00150", "required", 6, 7), ("00151", "required", 6, 8),
                    ("00152", "required", 4, 9), ("00153", "required", 4, 10),
                    ("00154", "required", 4, 11),
                ],
            },
            {
                "code": "120203K", "name": "会计学", "level": "bk",
                "school": "湖南大学", "total_credits": 74,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("04183", "required", 5, 4),
                    ("04184", "required", 4, 5), ("00155", "required", 8, 6),
                    ("00159", "required", 6, 7), ("00160", "required", 4, 8),
                    ("00161", "required", 5, 9), ("00162", "required", 5, 10),
                    ("00150", "elective", 6, 11),
                ],
            },
            {
                "code": "030101K", "name": "法学", "level": "bk",
                "school": "湘潭大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00226", "required", 4, 4),
                    ("00227", "required", 4, 5), ("00228", "required", 4, 6),
                    ("00230", "required", 5, 7), ("00246", "required", 6, 8),
                    ("00249", "required", 4, 9), ("00264", "required", 4, 10),
                ],
            },
            {
                "code": "040106", "name": "学前教育", "level": "bk",
                "school": "湖南师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00394", "required", 4, 4),
                    ("00398", "required", 6, 5), ("00401", "required", 6, 6),
                    ("00402", "required", 6, 7), ("00882", "required", 6, 8),
                    ("00467", "required", 6, 9),
                ],
            },
            {
                "code": "050101", "name": "汉语言文学", "level": "bk",
                "school": "湖南师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00537", "required", 6, 4),
                    ("00538", "required", 7, 5), ("00539", "required", 7, 6),
                    ("00540", "required", 6, 7), ("00541", "required", 6, 8),
                    ("00321", "required", 5, 9),
                ],
            },
            {
                "code": "080901", "name": "计算机科学与技术", "level": "bk",
                "school": "长沙理工大学", "total_credits": 73,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00023", "required", 10, 4),
                    ("02197", "required", 3, 5), ("02324", "required", 3, 6),
                    ("02325", "required", 4, 7), ("02326", "required", 5, 8),
                    ("04735", "required", 4, 9), ("04741", "required", 4, 10),
                    ("02333", "required", 3, 11),
                ],
            },
        ],
    },
    "51": {
        "province": "四川省",
        "schools": [
            {"name": "四川大学", "code": "10610"},
            {"name": "电子科技大学", "code": "10614"},
            {"name": "西南交通大学", "code": "10613"},
            {"name": "西南财经大学", "code": "10651"},
            {"name": "四川师范大学", "code": "10636"},
            {"name": "成都理工大学", "code": "10616"},
        ],
        "majors": [
            {
                "code": "120201K", "name": "工商管理", "level": "bk",
                "school": "西南财经大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00054", "required", 6, 4),
                    ("00067", "required", 6, 5), ("00149", "required", 6, 6),
                    ("00150", "required", 6, 7), ("00151", "required", 6, 8),
                    ("00152", "required", 4, 9), ("00153", "required", 4, 10),
                    ("00154", "required", 4, 11),
                ],
            },
            {
                "code": "030101K", "name": "法学", "level": "bk",
                "school": "四川大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00226", "required", 4, 4),
                    ("00227", "required", 4, 5), ("00230", "required", 5, 6),
                    ("00246", "required", 6, 7), ("00249", "required", 4, 8),
                    ("00228", "required", 4, 9), ("00263", "required", 4, 10),
                ],
            },
            {
                "code": "050101", "name": "汉语言文学", "level": "bk",
                "school": "四川师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00537", "required", 6, 4),
                    ("00538", "required", 7, 5), ("00539", "required", 7, 6),
                    ("00540", "required", 6, 7), ("00541", "required", 6, 8),
                    ("00321", "required", 5, 9),
                ],
            },
            {
                "code": "120203K", "name": "会计学", "level": "bk",
                "school": "西南财经大学", "total_credits": 74,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("04183", "required", 5, 4),
                    ("04184", "required", 4, 5), ("00155", "required", 8, 6),
                    ("00159", "required", 6, 7), ("00160", "required", 4, 8),
                    ("00161", "required", 5, 9), ("00162", "required", 5, 10),
                    ("00150", "elective", 6, 11),
                ],
            },
            {
                "code": "080901", "name": "计算机科学与技术", "level": "bk",
                "school": "电子科技大学", "total_credits": 73,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00023", "required", 10, 4),
                    ("02197", "required", 3, 5), ("02324", "required", 3, 6),
                    ("02325", "required", 4, 7), ("02326", "required", 5, 8),
                    ("04735", "required", 4, 9), ("04741", "required", 4, 10),
                    ("02333", "required", 3, 11),
                ],
            },
            {
                "code": "040106", "name": "学前教育", "level": "bk",
                "school": "四川师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00394", "required", 4, 4),
                    ("00398", "required", 6, 5), ("00401", "required", 6, 6),
                    ("00402", "required", 6, 7), ("00882", "required", 6, 8),
                    ("00467", "required", 6, 9),
                ],
            },
        ],
    },
    "32": {
        "province": "江苏省",
        "schools": [
            {"name": "南京大学", "code": "10284"},
            {"name": "南京财经大学", "code": "10327"},
            {"name": "南京师范大学", "code": "10319"},
            {"name": "苏州大学", "code": "10285"},
            {"name": "南京理工大学", "code": "10288"},
            {"name": "河海大学", "code": "10294"},
        ],
        "majors": [
            {
                "code": "120201K", "name": "工商管理", "level": "bk",
                "school": "南京大学", "total_credits": 73,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00054", "required", 6, 4),
                    ("00067", "required", 6, 5), ("00149", "required", 6, 6),
                    ("00150", "required", 6, 7), ("00151", "required", 6, 8),
                    ("00152", "required", 4, 9), ("00153", "required", 4, 10),
                    ("00154", "required", 4, 11),
                ],
            },
            {
                "code": "120203K", "name": "会计学", "level": "bk",
                "school": "南京财经大学", "total_credits": 74,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("04183", "required", 5, 4),
                    ("04184", "required", 4, 5), ("00155", "required", 8, 6),
                    ("00159", "required", 6, 7), ("00160", "required", 4, 8),
                    ("00161", "required", 5, 9), ("00162", "required", 5, 10),
                    ("00058", "elective", 5, 11),
                ],
            },
            {
                "code": "050101", "name": "汉语言文学", "level": "bk",
                "school": "南京师范大学", "total_credits": 70,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00537", "required", 6, 4),
                    ("00538", "required", 7, 5), ("00539", "required", 7, 6),
                    ("00540", "required", 6, 7), ("00541", "required", 6, 8),
                    ("00321", "required", 5, 9),
                ],
            },
            {
                "code": "030101K", "name": "法学", "level": "bk",
                "school": "苏州大学", "total_credits": 72,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00226", "required", 4, 4),
                    ("00227", "required", 4, 5), ("00230", "required", 5, 6),
                    ("00246", "required", 6, 7), ("00249", "required", 4, 8),
                    ("00228", "required", 4, 9), ("00262", "required", 3, 10),
                ],
            },
            {
                "code": "080901", "name": "计算机科学与技术", "level": "bk",
                "school": "南京理工大学", "total_credits": 73,
                "courses": [
                    ("03708", "required", 2, 1), ("03709", "required", 4, 2),
                    ("00015", "required", 14, 3), ("00023", "required", 10, 4),
                    ("02197", "required", 3, 5), ("02324", "required", 3, 6),
                    ("02325", "required", 4, 7), ("02326", "required", 5, 8),
                    ("04735", "required", 4, 9), ("04741", "required", 4, 10),
                ],
            },
        ],
    },
}


def seed() -> None:
    db = SessionLocal()
    try:
        total_majors = 0
        total_links = 0

        for province_code, pdata in DATA.items():
            # Ensure province
            province = db.query(Province).filter(Province.code == province_code).first()
            if not province:
                province = Province(code=province_code, name=pdata["province"])
                db.add(province)
                db.flush()
            province_id = province.id

            # Schools
            school_map = {}
            for s in pdata["schools"]:
                existing = db.query(School).filter(
                    School.name == s["name"], School.province_id == province_id
                ).first()
                if not existing:
                    obj = School(name=s["name"], province_id=province_id, code=s["code"])
                    db.add(obj)
                    db.flush()
                    school_map[s["name"]] = obj.id
                else:
                    school_map[s["name"]] = existing.id

            # Majors
            for m in pdata["majors"]:
                school_id = school_map.get(m["school"])
                if not school_id:
                    continue

                existing_major = (
                    db.query(Major)
                    .filter(
                        Major.code == m["code"],
                        Major.province_id == province_id,
                        Major.school_id == school_id,
                        Major.level == m["level"],
                    )
                    .first()
                )
                if existing_major:
                    major_id = existing_major.id
                else:
                    major_obj = Major(
                        code=m["code"], name=m["name"], level=m["level"],
                        province_id=province_id, school_id=school_id,
                        total_credits=m.get("total_credits"),
                    )
                    db.add(major_obj)
                    db.flush()
                    major_id = major_obj.id
                    total_majors += 1

                # Link courses
                for course_code, course_type, credits, sort_order in m["courses"]:
                    subject = db.query(Subject).filter(Subject.code == course_code).first()
                    if not subject:
                        from scripts.seed_hebei_data import COURSE_CATALOG
                        cat_name = COURSE_CATALOG.get(course_code, (f"未命名课程({course_code})", 0))[0]
                        subject = Subject(code=course_code, name=cat_name, category="public")
                        db.add(subject)
                        db.flush()

                    existing_link = (
                        db.query(MajorSubject)
                        .filter(MajorSubject.major_id == major_id, MajorSubject.subject_id == subject.id)
                        .first()
                    )
                    if not existing_link:
                        db.add(MajorSubject(
                            major_id=major_id, subject_id=subject.id,
                            course_type=course_type, credits=credits, sort_order=sort_order,
                        ))
                        total_links += 1

        db.commit()
        provinces_str = ", ".join(f"{DATA[c]['province']}" for c in DATA)
        print(f"[OK] Multi-province data imported!")
        print(f"   Provinces: {provinces_str}")
        print(f"   New majors: {total_majors}")
        print(f"   New course links: {total_links}")

    except Exception as e:
        db.rollback()
        print(f"[FAIL] Import failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
