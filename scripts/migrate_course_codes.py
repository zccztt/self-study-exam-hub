# -*- coding: utf-8 -*-
"""公共政治课新旧课程代码迁移。

背景: 2025-2026 年全国自学考试公共政治课改革,旧课程代码停用,新代码启用。
已通过旧课程的考生成绩可替代新课程,无需重考。

本脚本:
1. 确保新课程代码在 subjects 表中存在
2. 建立 subject_replacements 替代关系表
3. 把 major_subjects 从旧 Subject 迁移到新 Subject
4. 合并旧代码下的题目到新代码(更新 subject_id)
5. 更新 user_subject_status 中的关联(若有)

用法:
    python -m scripts.migrate_course_codes --dry-run
    python -m scripts.migrate_course_codes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.sql import func

from backend.database import SessionLocal
from backend.models import Base, Subject
from backend.models.enrollment import MajorSubject, UserSubjectStatus
from backend.models.question import Question


# ============================================================
# 公共政治课新旧替代映射 (旧代码 -> 新代码)
# ============================================================
# 来源: 全国高等教育自学考试委员会关于调整公共政治课课程的通知
# 生效: 2025 年起新计划统一使用新代码,旧代码成绩继续有效可替代

COURSE_REPLACEMENTS: list[dict] = [
    {
        "old_code": "03706",
        "old_name": "思想道德修养与法律基础",
        "new_code": "15042",
        "new_name": "思想道德与法治",
        "note": "专科公共课。已通过 03706 可替代 15042。",
    },
    {
        "old_code": "03708",
        "old_name": "中国近现代史纲要",
        "new_code": "15043",
        "new_name": "中国近现代史纲要",
        "note": "本科公共课。名称不变,代码更新。已通过 03708 可替代 15043。",
    },
    {
        "old_code": "03709",
        "old_name": "马克思主义基本原理概论",
        "new_code": "15044",
        "new_name": "马克思主义基本原理",
        "note": "本科公共课。已通过 03709 可替代 15044。",
    },
    {
        "old_code": "12656",
        "old_name": "毛泽东思想和中国特色社会主义理论体系概论",
        "new_code": "15041",
        "new_name": "毛泽东思想和中国特色社会主义理论体系概论",
        "note": "专科公共课。名称不变,代码更新。已通过 12656 可替代 15041。",
    },
]

# 15040 习近平新时代中国特色社会主义思想概论 为新增课程,无对应旧课程


def ensure_subjects(db) -> dict[str, int]:
    """确保新旧课程代码都在 subjects 表中, 返回 code->id 映射。"""
    code_to_id: dict[str, int] = {}
    all_codes = set()
    for r in COURSE_REPLACEMENTS:
        all_codes.add(r["old_code"])
        all_codes.add(r["new_code"])
    all_codes.add("15040")  # 新增课程

    for code in all_codes:
        subj = db.query(Subject).filter(Subject.code == code).first()
        if subj:
            code_to_id[code] = subj.id
        else:
            name = _code_name(code)
            subj = Subject(code=code, name=name)
            db.add(subj)
            db.flush()
            code_to_id[code] = subj.id
            print(f"  新建科目: {code} {name} (id={subj.id})")
    return code_to_id


def _code_name(code: str) -> str:
    for r in COURSE_REPLACEMENTS:
        if r["old_code"] == code:
            return r["old_name"]
        if r["new_code"] == code:
            return r["new_name"]
    if code == "15040":
        return "习近平新时代中国特色社会主义思想概论"
    return f"未知课程({code})"


def migrate_major_subjects(db, code_to_id: dict[str, int], dry_run: bool) -> int:
    """把 major_subjects 从旧 subject_id 迁移到新 subject_id。"""
    migrated = 0
    for r in COURSE_REPLACEMENTS:
        old_id = code_to_id.get(r["old_code"])
        new_id = code_to_id.get(r["new_code"])
        if not old_id or not new_id or old_id == new_id:
            continue

        links = db.query(MajorSubject).filter(MajorSubject.subject_id == old_id).all()
        for link in links:
            # 检查新代码是否已关联此专业
            exists = (
                db.query(MajorSubject)
                .filter(
                    MajorSubject.major_id == link.major_id,
                    MajorSubject.subject_id == new_id,
                )
                .first()
            )
            if exists:
                # 已有新代码关联, 删除旧的
                if not dry_run:
                    db.delete(link)
            else:
                # 迁移: 旧 -> 新
                if not dry_run:
                    link.subject_id = new_id
            migrated += 1
        if links:
            print(f"  {r['old_code']} -> {r['new_code']}: {len(links)} 条专业关联已迁移")
    return migrated


def migrate_questions(db, code_to_id: dict[str, int], dry_run: bool) -> int:
    """把旧代码下的题目 subject_id 指向新代码。"""
    migrated = 0
    for r in COURSE_REPLACEMENTS:
        old_id = code_to_id.get(r["old_code"])
        new_id = code_to_id.get(r["new_code"])
        if not old_id or not new_id or old_id == new_id:
            continue

        count = db.query(Question).filter(Question.subject_id == old_id).count()
        if count:
            if not dry_run:
                db.query(Question).filter(Question.subject_id == old_id).update(
                    {Question.subject_id: new_id}, synchronize_session=False
                )
            migrated += count
            print(f"  {r['old_code']} -> {r['new_code']}: {count} 道题目已迁移")
    return migrated


def migrate_user_status(db, code_to_id: dict[str, int], dry_run: bool) -> int:
    """把 user_subject_status 从旧代码迁移到新代码。"""
    migrated = 0
    for r in COURSE_REPLACEMENTS:
        old_id = code_to_id.get(r["old_code"])
        new_id = code_to_id.get(r["new_code"])
        if not old_id or not new_id or old_id == new_id:
            continue

        statuses = db.query(UserSubjectStatus).filter(UserSubjectStatus.subject_id == old_id).all()
        for status in statuses:
            exists = (
                db.query(UserSubjectStatus)
                .filter(
                    UserSubjectStatus.user_id == status.user_id,
                    UserSubjectStatus.subject_id == new_id,
                )
                .first()
            )
            if exists:
                # 新代码已有记录, 保留成绩更好的那条
                if status.status == "passed" and exists.status != "passed":
                    if not dry_run:
                        exists.status = status.status
                        exists.score = status.score
                        exists.exam_date = status.exam_date
                        exists.note = f"成绩来自旧课程 {r['old_code']}"
                if not dry_run:
                    db.delete(status)
            else:
                if not dry_run:
                    status.subject_id = new_id
                    status.note = f"成绩来自旧课程 {r['old_code']}。{status.note or ''}".strip()
            migrated += 1
        if statuses:
            print(f"  {r['old_code']} -> {r['new_code']}: {len(statuses)} 条学习状态已迁移")
    return migrated


def update_catalog(code_to_id: dict[str, int]) -> None:
    """更新 LEGACY_COURSE_CODE_ALIASES, 确保覆盖全部替代关系。"""
    from backend.data.self_exam_catalog import LEGACY_COURSE_CODE_ALIASES

    for r in COURSE_REPLACEMENTS:
        if r["old_code"] not in LEGACY_COURSE_CODE_ALIASES:
            print(f"  [提醒] LEGACY_COURSE_CODE_ALIASES 缺少 {r['old_code']} -> {r['new_code']}, 请手动补充")


def main() -> None:
    parser = argparse.ArgumentParser(description="公共政治课新旧课程代码迁移")
    parser.add_argument("--dry-run", action="store_true", help="只报告不写库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=== 公共政治课新旧课程代码迁移 ===")
        print()
        print("替代关系:")
        for r in COURSE_REPLACEMENTS:
            print(f"  {r['old_code']}({r['old_name']}) -> {r['new_code']}({r['new_name']})")
            print(f"    {r['note']}")
        print()

        print("1. 确保科目存在")
        code_to_id = ensure_subjects(db)
        print()

        print("2. 迁移专业-课程关联 (major_subjects)")
        ms = migrate_major_subjects(db, code_to_id, args.dry_run)
        print(f"   合计: {ms} 条" + (" [dry-run]" if args.dry_run else ""))
        print()

        print("3. 迁移题目 (questions.subject_id)")
        qs = migrate_questions(db, code_to_id, args.dry_run)
        print(f"   合计: {qs} 道" + (" [dry-run]" if args.dry_run else ""))
        print()

        print("4. 迁移学习状态 (user_subject_status)")
        us = migrate_user_status(db, code_to_id, args.dry_run)
        print(f"   合计: {us} 条" + (" [dry-run]" if args.dry_run else ""))
        print()

        print("5. 检查 LEGACY_COURSE_CODE_ALIASES")
        update_catalog(code_to_id)
        print()

        if not args.dry_run:
            db.commit()
            print("[OK] 迁移完成")
        else:
            print("[dry-run] 未写入数据库")
    finally:
        db.close()


if __name__ == "__main__":
    main()
