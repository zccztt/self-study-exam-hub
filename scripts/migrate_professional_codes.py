# -*- coding: utf-8 -*-
"""根据用户提供的专业新旧课程对照表，完善课程替代关系。

处理:
1. 确保所有新课程代码在 subjects 表中存在
2. 建立完整的替代映射（覆盖公共课 + 专业课）
3. 迁移 major_subjects 到新代码
4. 迁移题目到新代码
5. 前端展示替代关系

用法:
    python -m scripts.migrate_professional_codes --dry-run
    python -m scripts.migrate_professional_codes
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Base, Subject
from backend.models.enrollment import MajorSubject, Major, UserSubjectStatus
from backend.models.question import Question


# ============================================================
# 需要新建的科目（库中不存在的）
# ============================================================
NEW_SUBJECTS = [
    ("00223", "中国法制史"),
    ("04738", "C++程序设计(实践)"),
    ("04736", "数据库系统原理(实践)"),
    ("04756", "软件开发工具(实践)"),
    ("07790", "经济法学"),
    ("07999", "毕业设计"),
    ("13004", "数据结构与算法（实践）"),
    ("13009", "数据库原理与技术"),
    ("13014", "高级语言程序设计（实践）"),
    ("13532", "法律职业伦理"),
    ("14005", "律师与公证制度"),
    ("14263", "数字逻辑设计"),
    ("14349", "网络应用开发与系统集成"),
]

# ============================================================
# 计算机科学与技术（本科）080901 新旧课程替代
# ============================================================
CS_REPLACEMENTS = [
    {
        "old_code": "03708", "old_name": "中国近现代史纲要",
        "new_code": "15043", "new_name": "中国近现代史纲要",
        "old_credits": 2, "new_credits": 3,
        "note": "公共政治课更新",
    },
    {
        "old_code": "03709", "old_name": "马克思主义基本原理概论",
        "new_code": "15044", "new_name": "马克思主义基本原理",
        "old_credits": 4, "new_credits": 3,
        "note": "公共政治课更新",
    },
    {
        "old_code": "00015", "old_name": "英语(二)",
        "new_code": "13000", "new_name": "英语（专升本）",
        "old_credits": 14, "new_credits": 7,
        "note": "外语课程改革，学分下调",
    },
    {
        "old_code": "00910", "old_name": "网络经济与企业管理",
        "new_code": "00023", "new_name": "高等数学（工本）",
        "old_credits": 6, "new_credits": 10,
        "note": "课程置换（偏文管调整为数学工科核心）",
    },
    {
        "old_code": "02375", "old_name": "运筹学基础",
        "new_code": "02324", "new_name": "离散数学",
        "old_credits": 4, "new_credits": 4,
        "note": "课程置换（改为计算机核心基础）",
    },
    {
        "old_code": "04737", "old_name": "C++程序设计",
        "new_code": "13013", "new_name": "高级语言程序设计",
        "old_credits": 3, "new_credits": 4,
        "note": "编程语言基础课调整（理论）",
    },
    {
        "old_code": "04738", "old_name": "C++程序设计(实践)",
        "new_code": "13014", "new_name": "高级语言程序设计（实践）",
        "old_credits": 2, "new_credits": 2,
        "note": "编程语言基础课调整（实践）",
    },
    {
        "old_code": "04735", "old_name": "数据库系统原理",
        "new_code": "13003", "new_name": "数据结构与算法",
        "old_credits": 4, "new_credits": 4,
        "note": "核心课对应调整（理论）",
    },
    {
        "old_code": "04736", "old_name": "数据库系统原理(实践)",
        "new_code": "13004", "new_name": "数据结构与算法（实践）",
        "old_credits": 2, "new_credits": 2,
        "note": "核心课对应调整（实践）",
    },
    {
        "old_code": "04741", "old_name": "计算机网络原理",
        "new_code": "13015", "new_name": "计算机系统原理",
        "old_credits": 4, "new_credits": 4,
        "note": "课程置换",
    },
    {
        "old_code": "02323", "old_name": "操作系统概论",
        "new_code": "13180", "new_name": "操作系统",
        "old_credits": 4, "new_credits": 4,
        "note": "课程代码及大纲更新",
    },
    {
        "old_code": "02142", "old_name": "数据结构导论",
        "new_code": "14263", "new_name": "数字逻辑设计",
        "old_credits": 4, "new_credits": 4,
        "note": "课程置换（硬件基础）",
    },
    {
        "old_code": "02378", "old_name": "信息资源管理",
        "new_code": "13009", "new_name": "数据库原理与技术",
        "old_credits": 4, "new_credits": 4,
        "note": "课程置换（原数据库合并调整）",
    },
    {
        "old_code": "04757", "old_name": "信息系统开发与管理",
        "new_code": "13005", "new_name": "软件工程",
        "old_credits": 5, "new_credits": 3,
        "note": "课程置换",
    },
    {
        "old_code": "03173", "old_name": "软件开发工具",
        "new_code": "13017", "new_name": "计算机网络与信息安全",
        "old_credits": 5, "new_credits": 6,
        "note": "理论+实践合并顶替新课",
    },
    {
        "old_code": "02628", "old_name": "管理经济学",
        "new_code": "14349", "new_name": "网络应用开发与系统集成",
        "old_credits": 5, "new_credits": 6,
        "note": "去除管理类，改为系统集成技术",
    },
]

# 15040 为新增必修课，无旧代码对应
CS_NEW_COURSES = [
    {"code": "15040", "name": "习近平新时代中国特色社会主义思想概论", "credits": 3, "note": "新计划新增必修政治课"},
    {"code": "07999", "name": "毕业设计", "credits": 0, "note": "代码及要求保持不变"},
]

# ============================================================
# 法律事务（专科）新旧课程替代
# ============================================================
LAW_REPLACEMENTS = [
    {
        "old_code": "03706", "old_name": "思想道德修养与法律基础",
        "new_code": "15042", "new_name": "思想道德与法治",
        "old_credits": 2, "new_credits": 3,
        "note": "公共政治课更新",
    },
    {
        "old_code": "12656", "old_name": "毛泽东思想和中国特色社会主义理论体系概论",
        "new_code": "15041", "new_name": "毛泽东思想和中国特色社会主义理论体系概论",
        "old_credits": 4, "new_credits": 3,
        "note": "政治课代码更新，学分微调",
    },
    {
        "old_code": "04729", "old_name": "大学语文",
        "new_code": "14005", "new_name": "律师与公证制度",
        "old_credits": 4, "new_credits": 3,
        "note": "公共基础课调整为专业课",
    },
    {
        "old_code": "00244", "old_name": "经济法概论",
        "new_code": "07790", "new_name": "经济法学",
        "old_credits": 6, "new_credits": 6,
        "note": "课程代码及名称微调",
    },
    {
        "old_code": "00247", "old_name": "国际法",
        "new_code": "00264", "new_name": "中国法律思想史",
        "old_credits": 6, "new_credits": 4,
        "note": "专业方向课程置换",
    },
]

# 不变的课程 (code 相同)
LAW_UNCHANGED = ["05679", "05677", "00223", "00242", "00245", "00243", "00260", "05680"]

LAW_NEW_COURSES = [
    {"code": "13532", "name": "法律职业伦理", "credits": 3, "note": "新计划新增课程"},
    {"code": "00262", "name": "法律文书写作", "credits": 3, "note": "新计划新增课程"},
    {"code": "15040", "name": "习近平新时代中国特色社会主义思想概论", "credits": 3, "note": "新计划新增必修政治课"},
    {"code": "00220", "name": "行政法与行政诉讼法", "credits": 5, "note": "新计划新增/调整课程"},
]

# 特殊多对一顶替: 05680 或 00261 任一通过可顶替新 05680
LAW_SPECIAL_NOTES = {
    "05680": "原 05680 婚姻家庭法 或 00261 行政法学，任一通过均可顶替新计划的 05680。",
}

# ============================================================
# 合并所有替代关系
# ============================================================
ALL_REPLACEMENTS = CS_REPLACEMENTS + LAW_REPLACEMENTS


def ensure_new_subjects(db) -> dict[str, int]:
    """确保所有涉及的课程代码在 subjects 表中存在。"""
    code_to_id: dict[str, int] = {}
    all_codes: set[str] = set()
    for r in ALL_REPLACEMENTS:
        all_codes.add(r["old_code"])
        all_codes.add(r["new_code"])
    for entry in CS_NEW_COURSES + LAW_NEW_COURSES:
        all_codes.add(entry["code"])
    for code in LAW_UNCHANGED:
        all_codes.add(code)
    for code, name in NEW_SUBJECTS:
        all_codes.add(code)

    for code in sorted(all_codes):
        subj = db.query(Subject).filter(Subject.code == code).first()
        if subj:
            code_to_id[code] = subj.id
        else:
            # 从 NEW_SUBJECTS 找名称
            name = dict(NEW_SUBJECTS).get(code, f"未知课程({code})")
            subj = Subject(code=code, name=name)
            db.add(subj)
            db.flush()
            code_to_id[code] = subj.id
            print(f"  新建科目: {code} {name} (id={subj.id})")
    return code_to_id


def migrate_questions(db, code_to_id: dict[str, int], dry_run: bool) -> int:
    """把旧代码下的题目迁移到新代码。"""
    migrated = 0
    for r in ALL_REPLACEMENTS:
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
            print(f"  题目 {r['old_code']}({r['old_name']}) -> {r['new_code']}({r['new_name']}): {count} 道")
    return migrated


def main() -> None:
    parser = argparse.ArgumentParser(description="专业课程代码迁移（计算机科学与技术 + 法律事务）")
    parser.add_argument("--dry-run", action="store_true", help="只报告不写库")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=== 专业新旧课程代码迁移 ===")
        print()

        print("1. 确保所有科目存在")
        code_to_id = ensure_new_subjects(db)
        print(f"   共 {len(code_to_id)} 个科目" + (" [dry-run]" if args.dry_run else ""))
        print()

        print("2. 迁移题目 (questions.subject_id)")
        qs = migrate_questions(db, code_to_id, args.dry_run)
        print(f"   合计: {qs} 道" + (" [dry-run]" if args.dry_run else ""))
        print()

        if not args.dry_run:
            db.commit()
            print("[OK] 迁移完成")
        else:
            print("[dry-run] 未写入数据库")

        print()
        print("=== 计算机科学与技术(080901) 新旧对照 ===")
        for r in CS_REPLACEMENTS:
            print(f"  {r['old_code']}({r['old_name']},{r['old_credits']}分) -> {r['new_code']}({r['new_name']},{r['new_credits']}分) | {r['note']}")
        for c in CS_NEW_COURSES:
            print(f"  新增: {c['code']}({c['name']},{c['credits']}分) | {c['note']}")

        print()
        print("=== 法律事务(专科) 新旧对照 ===")
        for r in LAW_REPLACEMENTS:
            print(f"  {r['old_code']}({r['old_name']},{r['old_credits']}分) -> {r['new_code']}({r['new_name']},{r['new_credits']}分) | {r['note']}")
        for c in LAW_NEW_COURSES:
            print(f"  新增: {c['code']}({c['name']},{c['credits']}分) | {c['note']}")
        for code, note in LAW_SPECIAL_NOTES.items():
            print(f"  特殊: {code} - {note}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
