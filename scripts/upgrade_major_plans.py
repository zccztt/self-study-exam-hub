# -*- coding: utf-8 -*-
"""Upgrade major_subjects to new exam plans (2026).

This script:
1. Replaces old subject_ids with new ones in major_subjects (updates credits too)
2. Adds newly required courses (e.g. 15040) that have no old equivalent
3. Removes truly discontinued links
4. Recalculates major.total_credits
5. Syncs user_subject_status for affected enrollments

Usage:
    python -m scripts.upgrade_major_plans --dry-run
    python -m scripts.upgrade_major_plans
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Subject
from backend.models.enrollment import Major, MajorSubject, UserEnrollment, UserSubjectStatus


# ============================================================
# Full replacement map: old_code -> (new_code, new_credits)
# Covers public courses + CS + Law
# ============================================================

# Public political courses (apply to ALL majors)
PUBLIC_REPLACEMENTS = {
    "03706": ("15042", 3),   # 思想道德修养与法律基础 -> 思想道德与法治
    "03707": ("15041", 4),   # 毛概(专科旧版) -> 毛概(新)
    "03708": ("15043", 3),   # 中国近现代史纲要 -> 同名(新)
    "03709": ("15044", 3),   # 马克思主义基本原理概论 -> 马克思主义基本原理
    "12656": ("15041", 4),   # 毛概(另一旧代码) -> 毛概(新)
}

# CS (080901) professional course replacements
CS_REPLACEMENTS = {
    "00015": ("13000", 7),    # 英语(二) 14分 -> 英语(专升本) 7分
    "00910": ("00023", 10),   # 网络经济与企业管理 -> 高等数学(工本)
    "02375": ("02324", 4),    # 运筹学基础 -> 离散数学
    "04737": ("13013", 4),    # C++程序设计 -> 高级语言程序设计
    "04738": ("13014", 2),    # C++程序设计(实践) -> 高级语言程序设计(实践)
    "04735": ("13003", 4),    # 数据库系统原理 -> 数据结构与算法
    "04736": ("13004", 2),    # 数据库系统原理(实践) -> 数据结构与算法(实践)
    "04741": ("13015", 4),    # 计算机网络原理 -> 计算机系统原理
    "02323": ("13180", 4),    # 操作系统概论 -> 操作系统
    "02142": ("14263", 4),    # 数据结构导论 -> 数字逻辑设计
    "02378": ("13009", 4),    # 信息资源管理 -> 数据库原理与技术
    "04757": ("13005", 3),    # 信息系统开发与管理 -> 软件工程
    "03173": ("13017", 6),    # 软件开发工具 -> 计算机网络与信息安全
    "02628": ("14349", 6),    # 管理经济学 -> 网络应用开发与系统集成
}

# Law diploma professional course replacements
LAW_REPLACEMENTS = {
    "04729": ("14005", 3),    # 大学语文 -> 律师与公证制度 (only for law majors)
    "00244": ("07790", 6),    # 经济法概论 -> 经济法学
    "00247": ("00264", 4),    # 国际法 -> 中国法律思想史
}

# New courses to ADD (no old equivalent) per major code pattern
# (major_code_pattern, level, new_code, credits, course_type, sort_order_offset)
NEW_ADDITIONS = [
    # 15040 is required for all new plans
    ("*", "*", "15040", 3, "required", 0),
]

# CS-specific new additions
CS_NEW_ADDITIONS = [
    ("080901", "bk", "07999", 0, "required", 99),  # 毕业设计
]

# Law-specific new additions
LAW_NEW_ADDITIONS = [
    ("690206", "zk", "13532", 3, "required", 16),  # 法律职业伦理
    ("690206", "zk", "00262", 3, "required", 17),  # 法律文书写作
    ("690206", "zk", "00220", 5, "required", 18),  # 行政法与行政诉讼法
]


def get_subject_id(db, code: str, code_to_id: dict) -> int | None:
    """Get or cache subject id by code."""
    if code in code_to_id:
        return code_to_id[code]
    subj = db.query(Subject).filter(Subject.code == code).first()
    if subj:
        code_to_id[code] = subj.id
        return subj.id
    return None


def is_cs_major(major: Major) -> bool:
    return major.code == "080901"


def is_law_diploma(major: Major) -> bool:
    return major.code == "690206" and major.level == "zk"


def get_replacements_for_major(major: Major) -> dict:
    """Return the full old->new map applicable to a given major."""
    rmap = dict(PUBLIC_REPLACEMENTS)
    if is_cs_major(major):
        rmap.update(CS_REPLACEMENTS)
    if is_law_diploma(major):
        rmap.update(LAW_REPLACEMENTS)
    return rmap


def upgrade_major(db, major: Major, code_to_id: dict, dry_run: bool) -> dict:
    """Upgrade one major's subject plan. Returns stats."""
    stats = {"replaced": 0, "credits_updated": 0, "added": 0, "skipped": 0}
    rmap = get_replacements_for_major(major)

    # Get current links
    links = (
        db.query(MajorSubject)
        .filter(MajorSubject.major_id == major.id)
        .all()
    )

    # Build subject_id -> code map
    link_subject_ids = [lk.subject_id for lk in links]
    subjects = db.query(Subject).filter(Subject.id.in_(link_subject_ids)).all() if link_subject_ids else []
    id_to_code = {s.id: s.code for s in subjects}

    # Track which new codes already exist in this major
    existing_codes = set(id_to_code.values())

    # 1. Replace old -> new
    for link in links:
        old_code = id_to_code.get(link.subject_id)
        if not old_code or old_code not in rmap:
            continue

        new_code, new_credits = rmap[old_code]

        # Skip if new code already exists in this major (avoid duplicates)
        new_subject_id = get_subject_id(db, new_code, code_to_id)
        if not new_subject_id:
            print("    WARNING: subject %s not found in DB, skipping" % new_code)
            stats["skipped"] += 1
            continue

        already_has_new = (
            db.query(MajorSubject)
            .filter(MajorSubject.major_id == major.id, MajorSubject.subject_id == new_subject_id)
            .first()
        )

        if already_has_new and already_has_new.id != link.id:
            # New code already linked, just update its credits and remove old
            if already_has_new.credits != new_credits:
                print("    UPDATE credits: %s %s -> %s" % (new_code, already_has_new.credits, new_credits))
                if not dry_run:
                    already_has_new.credits = new_credits
                stats["credits_updated"] += 1
            print("    DELETE duplicate old link: %s (subject_id=%d)" % (old_code, link.subject_id))
            if not dry_run:
                db.delete(link)
            stats["replaced"] += 1
        else:
            # Replace in-place
            print("    REPLACE: %s(%.1f) -> %s(%.1f)" % (old_code, link.credits or 0, new_code, new_credits))
            if not dry_run:
                link.subject_id = new_subject_id
                link.credits = new_credits
            stats["replaced"] += 1

        existing_codes.add(new_code)

    # 2. Add new required courses
    additions = list(NEW_ADDITIONS)
    if is_cs_major(major):
        additions += CS_NEW_ADDITIONS
    if is_law_diploma(major):
        additions += LAW_NEW_ADDITIONS

    # Get max sort_order
    max_sort = max((lk.sort_order or 0) for lk in links) if links else 0

    for pattern, level_pat, new_code, credits, ctype, sort_offset in additions:
        if pattern != "*" and major.code != pattern:
            continue
        if level_pat != "*" and major.level != level_pat:
            continue
        if new_code in existing_codes:
            continue

        new_subject_id = get_subject_id(db, new_code, code_to_id)
        if not new_subject_id:
            print("    WARNING: new course %s not in subjects table" % new_code)
            continue

        sort_order = sort_offset if sort_offset > 0 else max_sort + 1
        max_sort = max(max_sort, sort_order)
        print("    ADD: %s (%s, %d credits)" % (new_code, ctype, credits))
        if not dry_run:
            db.add(MajorSubject(
                major_id=major.id,
                subject_id=new_subject_id,
                course_type=ctype,
                credits=credits,
                sort_order=sort_order,
            ))
        stats["added"] += 1
        existing_codes.add(new_code)

    # 3. Recalculate total_credits
    if not dry_run:
        db.flush()
        total = (
            db.query(MajorSubject)
            .filter(MajorSubject.major_id == major.id)
            .all()
        )
        new_total = sum(ms.credits or 0 for ms in total)
        if major.total_credits != new_total:
            print("    CREDITS: %s -> %s" % (major.total_credits, new_total))
            major.total_credits = new_total

    return stats


def sync_user_statuses(db, dry_run: bool) -> int:
    """After major plan upgrade, ensure user_subject_status rows match new plans."""
    synced = 0
    enrollments = db.query(UserEnrollment).filter(UserEnrollment.is_active.is_(True)).all()
    for enrollment in enrollments:
        # Get current major subjects
        ms_rows = (
            db.query(MajorSubject.subject_id)
            .filter(MajorSubject.major_id == enrollment.major_id)
            .all()
        )
        plan_subject_ids = {r[0] for r in ms_rows}

        # Get existing user statuses
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
        missing = plan_subject_ids - existing_ids
        for sid in missing:
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
    parser = argparse.ArgumentParser(description="Upgrade major plans to 2026 new exam codes")
    parser.add_argument("--dry-run", action="store_true", help="Report only, don't write")
    parser.add_argument("--major-id", type=int, help="Only upgrade a specific major")
    args = parser.parse_args()

    db = SessionLocal()
    code_to_id: dict[str, int] = {}

    try:
        print("=== Upgrade Major Plans to 2026 ===\n")

        # Find all active majors
        query = db.query(Major).filter(Major.is_active.is_(True))
        if args.major_id:
            query = query.filter(Major.id == args.major_id)
        majors = query.order_by(Major.id.asc()).all()
        print("Found %d active majors\n" % len(majors))

        total_stats = {"replaced": 0, "credits_updated": 0, "added": 0, "skipped": 0}

        for major in majors:
            print("  [%d] %s (%s) - %s" % (major.id, major.name, major.code, major.level))
            stats = upgrade_major(db, major, code_to_id, args.dry_run)
            for k in total_stats:
                total_stats[k] += stats[k]
            if all(v == 0 for v in stats.values()):
                print("    (no changes needed)")

        print("\n--- Summary ---")
        print("  Replaced:       %d" % total_stats["replaced"])
        print("  Credits updated: %d" % total_stats["credits_updated"])
        print("  Added:          %d" % total_stats["added"])
        print("  Skipped:        %d" % total_stats["skipped"])

        print("\nSyncing user_subject_status...")
        synced = sync_user_statuses(db, args.dry_run)
        print("  New status rows: %d" % synced)

        if not args.dry_run:
            db.commit()
            print("\n[OK] Upgrade complete!")
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
