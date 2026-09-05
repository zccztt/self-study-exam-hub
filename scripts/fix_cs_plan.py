# -*- coding: utf-8 -*-
"""Fix CS (080901) major plans to exactly match the official 2026 new-old comparison table.

Source: jisuanji.pdf

New plan for 计算机科学与技术 (080901, bk):
  Row  New_Code  New_Name                        Credits
  1    15043     中国近现代史纲要                  3
  2    15044     马克思主义基本原理                  3
  3    13000     英语(专升本)                      7
  4    00023     高等数学(工本)                    10
  5    02324     离散数学                          4
  6    13013     高级语言程序设计                    4
       13014     高级语言程序设计(实践)              2
  7    13003     数据结构与算法                      4
       13004     数据结构与算法(实践)                2
  8    13015     计算机系统原理                      4
  9    13180     操作系统                          4
  10   14263     数字逻辑设计                        4
  11   13009     数据库原理与技术                    4
  12   13005     软件工程                          3
  13   13017     计算机网络与信息安全                6
  14   14349     网络应用开发与系统集成              6
  15   15040     习近平新时代中国特色社会主义思想概论  3
  16   07999     毕业设计                          0

Usage:
    python -m scripts.fix_cs_plan --dry-run
    python -m scripts.fix_cs_plan
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Subject
from backend.models.enrollment import Major, MajorSubject, UserEnrollment, UserSubjectStatus


# The CORRECT new plan: (code, name, credits, course_type, sort_order)
CORRECT_CS_PLAN = [
    ("15043", "中国近现代史纲要", 3, "required", 1),
    ("15044", "马克思主义基本原理", 3, "required", 2),
    ("13000", "英语（专升本）", 7, "required", 3),
    ("00023", "高等数学（工本）", 10, "required", 4),
    ("02324", "离散数学", 4, "required", 5),
    ("13013", "高级语言程序设计", 4, "required", 6),
    ("13014", "高级语言程序设计（实践）", 2, "required", 7),
    ("13003", "数据结构与算法", 4, "required", 8),
    ("13004", "数据结构与算法（实践）", 2, "required", 9),
    ("13015", "计算机系统原理", 4, "required", 10),
    ("13180", "操作系统", 4, "required", 11),
    ("14263", "数字逻辑设计", 4, "required", 12),
    ("13009", "数据库原理与技术", 4, "required", 13),
    ("13005", "软件工程", 3, "required", 14),
    ("13017", "计算机网络与信息安全", 6, "required", 15),
    ("14349", "网络应用开发与系统集成", 6, "required", 16),
    ("15040", "习近平新时代中国特色社会主义思想概论", 3, "required", 17),
    ("07999", "毕业设计", 0, "required", 18),
]

# Correct old -> new replacement mapping (from PDF)
CORRECT_CS_REPLACEMENTS = {
    "03708": ("15043", "中国近现代史纲要", 2),         # old 2分 -> new 3分
    "03709": ("15044", "马克思主义基本原理概论", 4),     # old 4分 -> new 3分
    "00015": ("13000", "英语(二)", 14),               # old 14分 -> new 7分
    "00910": ("00023", "网络经济与企业管理", 6),        # old 6分 -> new 10分
    "02375": ("02324", "运筹学基础", 4),               # old 4分 -> new 4分
    "04737": ("13013", "C++程序设计", 3),              # old 3分 -> new 4分
    "04738": ("13014", "C++程序设计(实践)", 2),         # old 2分 -> new 2分
    "04735": ("13003", "数据库系统原理", 4),             # old 4分 -> new 4分
    "04736": ("13004", "数据库系统原理(实践)", 2),       # old 2分 -> new 2分
    "04741": ("13015", "计算机网络原理", 4),             # old 4分 -> new 4分
    "02323": ("13180", "操作系统概论", 4),              # old 4分 -> new 4分
    "02142": ("14263", "数据结构导论", 4),              # old 4分 -> new 4分
    "02378": ("13009", "信息资源管理", 4),              # old 4分 -> new 4分
    "04757": ("13005", "信息系统开发与管理", 5),         # old 5分 -> new 3分
    "03173": ("13017", "软件开发工具", 5),              # old 5分 -> new 6分
    "04756": ("13017", "软件开发工具(实践)", 1),         # old 1分, 合并入13017
    "02628": ("14349", "管理经济学", 5),               # old 5分 -> new 6分
}


def get_or_create_subject(db, code: str, name: str, code_to_id: dict) -> int:
    if code in code_to_id:
        return code_to_id[code]
    subj = db.query(Subject).filter(Subject.code == code).first()
    if subj:
        code_to_id[code] = subj.id
        return subj.id
    subj = Subject(code=code, name=name)
    db.add(subj)
    db.flush()
    code_to_id[code] = subj.id
    print("  NEW subject: %s %s (id=%d)" % (code, name, subj.id))
    return subj.id


def fix_major(db, major_id: int, code_to_id: dict, dry_run: bool) -> None:
    major = db.query(Major).filter(Major.id == major_id).first()
    if not major:
        print("  Major %d not found" % major_id)
        return
    print("\n  [%d] %s (%s, %s)" % (major_id, major.name, major.code, major.level))

    # Correct codes in new plan
    correct_codes = {row[0] for row in CORRECT_CS_PLAN}

    # Get existing links
    links = db.query(MajorSubject).filter(MajorSubject.major_id == major_id).all()
    existing_subject_ids = [lk.subject_id for lk in links]
    subjects = db.query(Subject).filter(Subject.id.in_(existing_subject_ids)).all() if existing_subject_ids else []
    id_to_code = {s.id: s.code for s in subjects}
    code_to_link = {id_to_code[lk.subject_id]: lk for lk in links if lk.subject_id in id_to_code}

    # 1. Remove courses not in new plan
    for lk in links:
        code = id_to_code.get(lk.subject_id, "?")
        if code not in correct_codes:
            print("    DELETE: %s (credits=%.1f, type=%s)" % (code, lk.credits or 0, lk.course_type))
            if not dry_run:
                db.delete(lk)

    if not dry_run:
        db.flush()

    # 2. Add or update each course in new plan
    for code, name, credits, ctype, sort_order in CORRECT_CS_PLAN:
        sid = get_or_create_subject(db, code, name, code_to_id)

        existing = (
            db.query(MajorSubject)
            .filter(MajorSubject.major_id == major_id, MajorSubject.subject_id == sid)
            .first()
        )
        if existing:
            # Update if needed
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
            print("    ADD:    %s %s (credits=%d, %s, sort=%d)" % (code, name, credits, ctype, sort_order))
            if not dry_run:
                db.add(MajorSubject(
                    major_id=major_id,
                    subject_id=sid,
                    course_type=ctype,
                    credits=credits,
                    sort_order=sort_order,
                ))

    # 3. Update total_credits
    if not dry_run:
        db.flush()
        all_ms = db.query(MajorSubject).filter(MajorSubject.major_id == major_id).all()
        new_total = sum(ms.credits or 0 for ms in all_ms)
        if major.total_credits != new_total:
            print("    TOTAL: %s -> %s" % (major.total_credits, new_total))
            major.total_credits = new_total


def sync_user_statuses(db, major_id: int, dry_run: bool) -> int:
    """Ensure user_subject_status rows match new plan."""
    synced = 0
    enrollments = (
        db.query(UserEnrollment)
        .filter(UserEnrollment.major_id == major_id, UserEnrollment.is_active.is_(True))
        .all()
    )
    for enrollment in enrollments:
        ms_rows = (
            db.query(MajorSubject.subject_id)
            .filter(MajorSubject.major_id == major_id)
            .all()
        )
        plan_subject_ids = {r[0] for r in ms_rows}

        existing = (
            db.query(UserSubjectStatus.subject_id)
            .filter(
                UserSubjectStatus.enrollment_id == enrollment.id,
                UserSubjectStatus.user_id == enrollment.user_id,
            )
            .all()
        )
        existing_ids = {r[0] for r in existing}

        # Add missing
        for sid in plan_subject_ids - existing_ids:
            if not dry_run:
                db.add(UserSubjectStatus(
                    user_id=enrollment.user_id,
                    subject_id=sid,
                    enrollment_id=enrollment.id,
                    status="not_taken",
                ))
            synced += 1
    return synced


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix CS (080901) major plans to match official 2026 table")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--major-id", type=int, help="Fix only one specific major (default: all 080901)")
    args = parser.parse_args()

    db = SessionLocal()
    code_to_id: dict[str, int] = {}

    try:
        print("=== Fix CS (080901) Major Plans ===\n")

        if args.major_id:
            major_ids = [args.major_id]
        else:
            majors = db.query(Major).filter(Major.code == "080901", Major.is_active.is_(True)).all()
            major_ids = [m.id for m in majors]
            print("Found %d CS majors (080901)" % len(major_ids))

        for mid in major_ids:
            fix_major(db, mid, code_to_id, args.dry_run)

        print("\nSyncing user_subject_status...")
        total_synced = 0
        for mid in major_ids:
            total_synced += sync_user_statuses(db, mid, args.dry_run)
        print("  New status rows: %d" % total_synced)

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
