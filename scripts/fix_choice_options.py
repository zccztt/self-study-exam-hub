# -*- coding: utf-8 -*-
"""修复选择题选项数据：拆分合并选项、截断超长选项、清理多题合并记录。"""

import json
import re
import sqlite3
import sys

DB_PATH = "exam_hub.db"


def normalize_options(options: list) -> list:
    """将合并的选项拆分为独立选项。"""
    if not options:
        return []

    # 已经是 3-6 个选项：正常
    if 3 <= len(options) <= 6:
        return options

    # 1-2 个选项：尝试按 B./C./D./E./F. 拆分
    if len(options) <= 2:
        all_text = []
        for opt in options:
            s = str(opt).strip()
            parts = re.split(r"\s+([B-F])[.、]\s*", s)
            if len(parts) >= 3:
                all_text.append(parts[0].strip())
                for i in range(1, len(parts), 2):
                    if i + 1 < len(parts) and parts[i + 1].strip():
                        all_text.append(parts[i + 1].strip())
            elif s:
                all_text.append(s)
        if len(all_text) >= 3:
            return all_text[:6]
        return options

    # >6 个选项：多题合并到一条记录，尝试提取前 4 个有效选项
    # 常见模式：第一个选项可能含 "B. xxx" 格式
    first = str(options[0]).strip()
    parts = re.split(r"\s+([B-F])[.、]\s*", first)
    if len(parts) >= 3:
        # 第一个元素自身就包含 A/B/C/D 选项
        result = [parts[0].strip()]
        for i in range(1, len(parts), 2):
            if i + 1 < len(parts) and parts[i + 1].strip():
                result.append(parts[i + 1].strip())
        return result[:4]
    else:
        # 取前 4 个作为选项
        return [str(o).strip() for o in options[:4]]


def main():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 查找所有选项数 != 4 的选择题
    cur.execute(
        "SELECT id, options, answer FROM questions "
        "WHERE question_type IN ('single_choice', 'multiple_choice') "
        "AND json_array_length(options) != 4"
    )
    rows = cur.fetchall()
    print(f"找到 {len(rows)} 道选项数 != 4 的选择题")

    fixed = 0
    deleted = 0
    skipped_judge = 0
    skipped_other = 0

    for row in rows:
        qid, opts_raw, answer = row
        opts = json.loads(opts_raw) if opts_raw else []
        n = len(opts)

        # 判断题（2选项，正确/错误类）保留不动
        if n == 2:
            texts = {str(o).strip().lower() for o in opts}
            if texts <= {'正确', '错误', 'true', 'false', '对', '错', 'not given'}:
                skipped_judge += 1
                continue

        # 3选项 True/False/Not Given 也保留
        if n == 3:
            texts = {str(o).strip().lower() for o in opts}
            if texts <= {'true', 'false', 'not given', 'truc'}:  # truc 是 True 的 typo
                skipped_judge += 1
                continue

        # 5选项且有实际内容的保留（某些科目确实有5选项题）
        if n == 5:
            # 检查是否有多余的选项（如带冒号、解释性文本）
            clean = [str(o).strip() for o in opts if str(o).strip()]
            # 尝试看最后一个是否是解释性内容
            last = clean[-1] if clean else ""
            if re.match(r'^[A-F][:：]', last) or len(last) > 100:
                # 最后一个是脏数据，取前4个
                new_opts = clean[:4]
                cur.execute(
                    "UPDATE questions SET options = ? WHERE id = ?",
                    (json.dumps(new_opts, ensure_ascii=False), qid)
                )
                fixed += 1
            else:
                # 真的5选项，保留
                skipped_other += 1
            continue

        # 超长选项（>6）：多题合并到一条记录
        if n > 6:
            new_opts = normalize_options(opts)
            if len(new_opts) >= 3:
                cur.execute(
                    "UPDATE questions SET options = ? WHERE id = ?",
                    (json.dumps(new_opts, ensure_ascii=False), qid)
                )
                fixed += 1
            else:
                # 无法修复，删除这些垃圾记录
                cur.execute("DELETE FROM questions WHERE id = ?", (qid,))
                deleted += 1
            continue

        # 2选项合并模式
        if n <= 2:
            new_opts = normalize_options(opts)
            if len(new_opts) >= 3:
                cur.execute(
                    "UPDATE questions SET options = ? WHERE id = ?",
                    (json.dumps(new_opts, ensure_ascii=False), qid)
                )
                fixed += 1
            else:
                skipped_other += 1
            continue

        # 3选项：可能缺少一个选项，也可能是真的3选项
        if n == 3:
            skipped_other += 1
            continue

        # 6选项
        if n == 6:
            # 取前4个
            new_opts = [str(o).strip() for o in opts[:4]]
            cur.execute(
                "UPDATE questions SET options = ? WHERE id = ?",
                (json.dumps(new_opts, ensure_ascii=False), qid)
            )
            fixed += 1
            continue

    conn.commit()

    # 验证结果
    cur.execute(
        "SELECT json_array_length(options) as n, COUNT(*) "
        "FROM questions WHERE question_type IN ('single_choice', 'multiple_choice') "
        "GROUP BY n ORDER BY n"
    )
    print(f"\n修复完成: fixed={fixed}, deleted={deleted}, skipped_judge={skipped_judge}, skipped_other={skipped_other}")
    print("\n修复后选项分布:")
    for row in cur.fetchall():
        mark = ' ✓' if row[0] == 4 else (' (判断/TF)' if row[0] in (2, 3) else '')
        print(f"  {row[0]} options: {row[1]}{mark}")

    conn.close()


if __name__ == "__main__":
    main()
