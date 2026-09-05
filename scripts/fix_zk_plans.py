# -*- coding: utf-8 -*-
"""Fix law/admin diploma plans based on official PDF.

Problem: upgrade_major_plans.py incorrectly added law-specific courses to
行政管理(690206) zk. The PDF (kkzyWjView.pdf) is actually for 法律事务 zk.

This script:
1. Fixes 行政管理(690206) zk - remove law courses, restore correct admin plan
2. Creates 法律事务 zk major if it doesn't exist, with correct plan from PDF

Usage:
    python -m scripts.fix_zk_plans --dry-run
    python -m scripts.fix_zk_plans
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Subject
from backend.models.enrollment import Major, MajorSubject, Province, School, UserEnrollment, UserSubjectStatus


# ============================================================
# 行政管理 专科 (690206) 正确课程计划
# 来源: 河北省教育考试院
# ============================================================
ADMIN_ZK_PLAN = [
    ("15042", "思想道德与法治", 3, "required", 1),
    ("15041", "毛泽东思想和中国特色社会主义理论体系概论", 4, "required", 2),
    ("04729", "大学语文", 4, "required", 3),
    ("00018", "计算机应用基础", 2, "required", 4),
    ("00107", "现代管理学", 6, "required", 5),
    ("00277", "行政管理学", 6, "required", 6),
    ("00292", "市政学", 6, "required", 7),
    ("00312", "政治学概论", 6, "required", 8),
    ("00341", "公文写作与处理", 6, "required", 9),
    ("00163", "管理心理学", 5, "required", 10),
    ("00182", "公共关系学", 4, "required", 11),
    ("00261", "行政法学", 5, "elective", 12),
    ("00266", "社会学概论", 6, "elective", 13),
    ("00071", "社会保障概论", 5, "elective", 14),
    ("15040", "习近平新时代中国特色社会主义思想概论", 3, "required", 15),
]

# ============================================================
# 法律事务 专科 正确课程计划 (from PDF: kkzyWjView.pdf)
# ============================================================
LAW_ZK_PLAN = [
    ("15042", "思想道德与法治", 3, "required", 1),
    ("15041", "毛泽东思想和中国特色社会主义理论体系概论", 3, "required", 2),
    ("05679", "宪法学", 4, "required", 3),
    ("05677", "法理学", 7, "required", 4),
    ("00223", "中国法制史", 5, "required", 5),
    ("00242", "民法学", 7, "required", 6),
    ("00245", "刑法学", 7, "required", 7),
    ("00243", "民事诉讼法学", 5, "required", 8),
    ("00260", "刑事诉讼法学", 4, "required", 9),
    ("05680", "婚姻家庭法", 3, "required", 10),
    ("14005", "律师与公证制度", 3, "required", 11),
    ("07790", "经济法学", 6, "required", 12),
    ("00264", "中国法律思想史", 4, "required", 13),
    ("13532", "法律职业伦理", 3, "required", 14),
    ("00262", "法律文书写作", 3, "required", 15),
    ("15040", "习近平新时代中国特色社会主义思想概论", 3, "required", 16),
    ("00220", "行政法与行政诉讼法", 5, "required", 17),
]

# Old -> new replacement for law diploma
LAW_ZK_REPLACEMENTS = {
    "03706": "15042",   # 思想道德修养与法律基础 -> 思想道德与法治
    "12656": "15041",   # 毛概(旧) -> 毛概(新)
    "04729": "14005",   # 大学语文 -> 律师与公证制度
    "00244": "07790",   # 经济法概论 -> 经济法学
    "00247": "00264",   # 国际法 -> 中国法律思想史
}


def get_or_create_subject(db, code, name, cache):
    if code in cache:
        return cache[code]
    subj = db.query(Subject).filter(Subject.code == code).first()
    if subj:
        cache[code] = subj.id
        return subj.id
    subj = Subject(code=code, name=name)
    db.add(subj)
    db.flush()
    cache[code] = subj.id
    print("  NEW subject: %s %s (id=%d)" % (code, name, subj.id))
    return subj.id


def set_major_plan(db, major_id, plan, code_cache, dry_run):
    """Replace a major's entire course plan with the given plan."""
    major = db.query(Major).filter(Major.id == major_id).first()
    if not major:
        return

    correct_codes = {row[0] for row in plan}

    # Get existing
    links = db.query(MajorSubject).filter(MajorSubject.major_id == major_id).all()
    existing_ids = [lk.subject_id for lk in links]
    subjects = db.query(Subject).filter(Subject.id.in_(existing_ids)).all() if existing_ids else []
    id_to_code = {s.id: s.code for s in subjects}

    # Delete courses not in plan
    for lk in links:
        code = id_to_code.get(lk.subject_id, "?")
        if code not in correct_codes:
            print("    DELETE: %s (credits=%.1f)" % (code, lk.credits or 0))
            if not dry_run:
                db.delete(lk)

    if not dry_run:
        db.flush()

    # Add or update
    for code, name, credits, ctype, sort_order in plan:
        sid = get_or_create_subject(db, code, name, code_cache)
        existing = (
            db.query(MajorSubject)
            .filter(MajorSubject.major_id == major_id, MajorSubject.subject_id == sid)
            .first()
        )
        if existing:
            changed = []
            if existing.credits != credits:
                changed.append("credits %.1f->%d" % (existing.credits or 0, credits))
                if not dry_run:
                    existing.credits = credits
            if existing.course_type != ctype:
                changed.append("type %s->%s" % (existing.course_type, ctype))
                if not dry_run:
                    existing.course_type = ctype
            if existing.sort_order != sort_order:
                changed.append("sort %s->%d" % (existing.sort_order, sort_order))
                if not dry_run:
                    existing.sort_order = sort_order
            if changed:
                print("    UPDATE: %s %s - %s" % (code, name, ", ".join(changed)))
        else:
            print("    ADD:    %s %s (credits=%d, %s)" % (code, name, credits, ctype))
            if not dry_run:
                db.add(MajorSubject(
                    major_id=major_id,
                    subject_id=sid,
                    course_type=ctype,
                    credits=credits,
                    sort_order=sort_order,
                ))

    # Recalc total
    if not dry_run:
        db.flush()
        all_ms = db.query(MajorSubject).filter(MajorSubject.major_id == major_id).all()
        new_total = sum(ms.credits or 0 for ms in all_ms)
        if major.total_credits != new_total:
            print("    TOTAL: %s -> %s" % (major.total_credits, new_total))
            major.total_credits = new_total


def sync_user_statuses(db, major_id, dry_run):
    synced = 0
    enrollments = (
        db.query(UserEnrollment)
        .filter(UserEnrollment.major_id == major_id, UserEnrollment.is_active.is_(True))
        .all()
    )
    for enrollment in enrollments:
        ms_rows = db.query(MajorSubject.subject_id).filter(MajorSubject.major_id == major_id).all()
        plan_ids = {r[0] for r in ms_rows}
        existing = (
            db.query(UserSubjectStatus.subject_id)
            .filter(
                UserSubjectStatus.enrollment_id == enrollment.id,
                UserSubjectStatus.user_id == enrollment.user_id,
            )
            .all()
        )
        existing_ids = {r[0] for r in existing}
        for sid in plan_ids - existing_ids:
            if not dry_run:
                db.add(UserSubjectStatus(
                    user_id=enrollment.user_id,
                    subject_id=sid,
                    enrollment_id=enrollment.id,
                    status="not_taken",
                ))
            synced += 1
    return synced


def main():
    parser = argparse.ArgumentParser(description="Fix zk major plans")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    code_cache = {}

    try:
        print("=== Fix Diploma (zk) Major Plans ===\n")

        # 1. Fix 行政管理 (690206) zk - remove law courses
        admin_majors = db.query(Major).filter(
            Major.code == "690206", Major.level == "zk", Major.is_active.is_(True)
        ).all()
        print("--- 行政管理 专科 (690206) ---")
        print("Found %d majors" % len(admin_majors))
        for m in admin_majors:
            print("\n  [%d] %s" % (m.id, m.name))
            set_major_plan(db, m.id, ADMIN_ZK_PLAN, code_cache, args.dry_run)
            sync_user_statuses(db, m.id, args.dry_run)

        # 2. Create or fix 法律事务 zk
        print("\n--- 法律事务 专科 ---")
        # Check if it exists already
        law_zk = db.query(Major).filter(
            Major.name.like("%法律事务%"), Major.level == "zk", Major.is_active.is_(True)
        ).first()

        if not law_zk:
            # Find Hebei province and a suitable school
            province = db.query(Province).filter(Province.code == "13").first()
            if not province:
                print("  ERROR: Province 13 (河北) not found")
            else:
                # Use 河北大学 as default school for law
                school = db.query(School).filter(
                    School.name == "河北大学", School.province_id == province.id
                ).first()
                if not school:
                    print("  ERROR: School 河北大学 not found")
                else:
                    print("  Creating 法律事务 专科 major...")
                    if not args.dry_run:
                        law_zk = Major(
                            code="680503",
                            name="法律事务",
                            level="zk",
                            province_id=province.id,
                            school_id=school.id,
                            total_credits=0,
                        )
                        db.add(law_zk)
                        db.flush()
                        print("  Created major id=%d" % law_zk.id)

        if law_zk:
            print("\n  [%d] %s (code=%s)" % (law_zk.id, law_zk.name, law_zk.code))
            set_major_plan(db, law_zk.id, LAW_ZK_PLAN, code_cache, args.dry_run)
            sync_user_statuses(db, law_zk.id, args.dry_run)

        if not args.dry_run:
            db.commit()
            print("\n[OK] Done!")
        else:
            print("\n[dry-run] No changes written.")

    except Exception as e:
        db.rollback()
        print("[FAIL] %s" % e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
