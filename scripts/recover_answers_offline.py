# -*- coding: utf-8 -*-
"""离线恢复选择题答案 —— 不联网，仅利用库内已有信息。

两条恢复路径：
  1. stem_extracted —— 爬虫把答案字母误拼进了题干末尾，提取后从题干剥离
  2. db_matched     —— 同题干同科目的重复题中已有真实答案，直接沿用

用法：
    python -m scripts.recover_answers_offline --dry-run   # 只报告不写库
    python -m scripts.recover_answers_offline             # 执行修复
"""

import argparse
import json
import re
import sqlite3
import sys

DB_PATH = "exam_hub.db"
PLACEHOLDER = "待核实"
MIN_STEM_LENGTH = 6  # 清理后题干的最小长度（自考存在 7-9 字的合法短题干）

# 题干末尾紧跟中文/是/为/括号/引号之后的孤立 A-D 字母
TAIL_LETTER_RE = re.compile(r"(?<=[一-龥是为）)\"”\'’])\s*([A-D])\s*$")
# 题干内显式的答案标记
INLINE_ANSWER_RE = re.compile(r"(?:【答案】|正确答案|答案)[：:]\s*([A-D]{1,4})")


def normalize_stem(text: str) -> str:
    """归一化题干用于跨记录比对。"""
    return re.sub(r"[\s　（）()【】、,，.。；;：:？?\"”\'’]+", "", text or "")


def recover_from_stem(cur) -> list:
    """路径1：从题干末尾提取答案字母，并返回清理后的题干。"""
    cur.execute(
        "SELECT id, content, options, question_type FROM questions "
        "WHERE answer = ? AND question_type IN ('single_choice', 'multiple_choice')",
        (PLACEHOLDER,),
    )
    fixes = []
    for qid, content, opts_raw, qtype in cur.fetchall():
        stem = (content or "").rstrip()
        match = TAIL_LETTER_RE.search(stem)
        if not match:
            continue
        letter = match.group(1)
        cleaned = TAIL_LETTER_RE.sub("", stem).rstrip()
        options = json.loads(opts_raw) if opts_raw else []

        # 安全校验：题干仍有效、答案在选项范围内、清理后不残留字母
        if len(cleaned) < MIN_STEM_LENGTH:
            continue
        if options and ord(letter) - 65 >= len(options):
            continue
        if re.search(r"[A-D]\s*$", cleaned):
            continue

        fixes.append({
            "id": qid,
            "answer": letter,
            "content": cleaned,
            "source": "stem_extracted",
        })
    return fixes


def recover_from_duplicates(cur, already_fixed: set) -> list:
    """路径2：同题干同科目的重复题中已有真实答案，沿用之。"""
    cur.execute(
        "SELECT id, subject_id, content, answer FROM questions "
        "WHERE answer <> ? AND trim(answer) <> '' "
        "AND question_type IN ('single_choice', 'multiple_choice')",
        (PLACEHOLDER,),
    )
    index = {}
    for qid, sid, content, answer in cur.fetchall():
        key = normalize_stem(content)[:50]
        if len(key) < 12:
            continue
        index.setdefault((sid, key), (qid, answer))

    cur.execute(
        "SELECT id, subject_id, content FROM questions "
        "WHERE answer = ? AND question_type IN ('single_choice', 'multiple_choice')",
        (PLACEHOLDER,),
    )
    fixes = []
    for qid, sid, content in cur.fetchall():
        if qid in already_fixed:
            continue
        key = normalize_stem(content)[:50]
        if len(key) < 12:
            continue
        hit = index.get((sid, key))
        if not hit:
            continue
        fixes.append({
            "id": qid,
            "answer": hit[1],
            "content": None,  # 题干无需改动
            "source": "db_matched",
            "from_id": hit[0],
        })
    return fixes


def main() -> None:
    parser = argparse.ArgumentParser(description="离线恢复选择题答案")
    parser.add_argument("--dry-run", action="store_true", help="只报告，不写库")
    args = parser.parse_args()

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM questions WHERE answer = ?", (PLACEHOLDER,))
    before = cur.fetchone()[0]

    stem_fixes = recover_from_stem(cur)
    dup_fixes = recover_from_duplicates(cur, {f["id"] for f in stem_fixes})
    all_fixes = stem_fixes + dup_fixes

    print(f"待核实题目总数: {before}")
    print(f"  路径1 题干提取: {len(stem_fixes)}")
    print(f"  路径2 库内互补: {len(dup_fixes)}")
    print(f"  合计可恢复: {len(all_fixes)}")

    if args.dry_run:
        print("\n[dry-run] 未写入数据库。样本：")
        for fix in all_fixes[:5]:
            print(f"  id={fix['id']} answer={fix['answer']} source={fix['source']}")
        conn.close()
        return

    explanation_note = "答案由题库离线校验恢复。"
    for fix in all_fixes:
        if fix["content"] is not None:
            cur.execute(
                "UPDATE questions SET answer = ?, content = ?, answer_source = ?, "
                "explanation = ? WHERE id = ?",
                (fix["answer"], fix["content"], fix["source"], explanation_note, fix["id"]),
            )
        else:
            cur.execute(
                "UPDATE questions SET answer = ?, answer_source = ?, explanation = ? "
                "WHERE id = ?",
                (fix["answer"], fix["source"], explanation_note, fix["id"]),
            )
    conn.commit()

    cur.execute("SELECT COUNT(*) FROM questions WHERE answer = ?", (PLACEHOLDER,))
    after = cur.fetchone()[0]
    print(f"\n修复完成: {before} -> {after} (恢复 {before - after} 道)")

    cur.execute("SELECT answer_source, COUNT(*) FROM questions GROUP BY answer_source")
    print("\nanswer_source 分布:")
    for row in cur.fetchall():
        print(f"  {row[0]}: {row[1]}")

    conn.close()


if __name__ == "__main__":
    main()
