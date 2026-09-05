# -*- coding: utf-8 -*-
"""Fix credits for majors that already had new course codes but with old credit values.

Usage:
    python -m scripts.fix_credits --dry-run
    python -m scripts.fix_credits
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Subject
from backend.models.enrollment import Major, MajorSubject


# Correct credits for new-plan courses (code -> correct_credits)
# Based on 2026 national exam plan
CORRECT_CREDITS = {
    # Public political courses
    "15040": 3,   # 习近平新时代中国特色社会主义思想概论
    "15041": 4,   # 毛泽东思想和中国特色社会主义理论体系概论
    "15042": 3,   # 思想道德与法治 (was 2 under old 03706)
    "15043": 3,   # 中国近现代史纲要 (was 2 under old 03708)
    "15044": 3,   # 马克思主义基本原理 (was 4 under old 03709)
    # CS courses
    "13000": 7,   # 英语(专升本) (was 14 under old 00015)
    "13003": 4,   # 数据结构与算法
    "13004": 2,   # 数据结构与算法(实践)
    "13005": 3,   # 软件工程
    "13009": 4,   # 数据库原理与技术
    "13013": 4,   # 高级语言程序设计 (was 3)
    "13014": 2,   # 高级语言程序设计(实践)
    "13015": 4,   # 计算机系统原理
    "13017": 6,   # 计算机网络与信息安全
    "13180": 4,   # 操作系统
    "14263": 4,   # 数字逻辑设计
    "14349": 6,   # 网络应用开发与系统集成
    # Law courses
    "14005": 3,   # 律师与公证制度
    "07790": 6,   # 经济法学
    "13532": 3,   # 法律职业伦理
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Fix credits to match 2026 new plan")
    parser.add_argument("--dry-run", action="store_true", help="Report only")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=== Fix Credits to 2026 Plan ===\n")

        # Get subject id map for codes we care about
        subjects = db.query(Subject).filter(Subject.code.in_(list(CORRECT_CREDITS.keys()))).all()
        code_by_id = {s.id: s.code for s in subjects}
        id_by_code = {s.code: s.id for s in subjects}

        fixed = 0
        subject_ids = list(code_by_id.keys())

        # Find all major_subject rows with these subjects
        links = (
            db.query(MajorSubject)
            .filter(MajorSubject.subject_id.in_(subject_ids))
            .all()
        ) if subject_ids else []

        for link in links:
            code = code_by_id.get(link.subject_id)
            if not code:
                continue
            correct = CORRECT_CREDITS[code]
            if link.credits != correct:
                major = db.query(Major).filter(Major.id == link.major_id).first()
                mname = major.name if major else "?"
                print("  [%d] %s: %s credits %.1f -> %d" % (link.major_id, mname, code, link.credits or 0, correct))
                if not args.dry_run:
                    link.credits = correct
                fixed += 1

        print("\nFixed %d credit values" % fixed)

        # Recalculate total_credits for all affected majors
        if not args.dry_run and fixed > 0:
            db.flush()
            affected_major_ids = set(lk.major_id for lk in links if code_by_id.get(lk.subject_id))
            for mid in sorted(affected_major_ids):
                all_ms = db.query(MajorSubject).filter(MajorSubject.major_id == mid).all()
                new_total = sum(ms.credits or 0 for ms in all_ms)
                major = db.query(Major).filter(Major.id == mid).first()
                if major and major.total_credits != new_total:
                    print("  [%d] %s total_credits: %s -> %s" % (mid, major.name, major.total_credits, new_total))
                    major.total_credits = new_total

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
