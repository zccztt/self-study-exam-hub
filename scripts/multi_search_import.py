# -*- coding: utf-8 -*-
"""Search real papers using multi-source search client and import to DB.

Usage:
    python -m scripts.multi_search_import
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.search_client import search_client

# Priority subjects for Hebei University
SUBJECTS = [
    ("00277", "行政管理学"),
    ("03709", "马克思主义基本原理概论"),
    ("03708", "中国近现代史纲要"),
    ("00315", "当代中国政治制度"),
    ("02331", "数据结构"),
    ("04741", "计算机网络原理"),
    ("00107", "现代管理学"),
    ("00152", "组织行为学"),
    ("00320", "领导科学"),
    ("00230", "合同法"),
]

# Search queries for different periods
SEARCH_PERIODS = [
    (2024, 10),
    (2025, 4),
]


def parse_questions(text):
    """Parse questions from extracted content."""
    questions = []
    sc_start = text.find("单项选择题")
    if sc_start < 0:
        sc_start = text.find("一、")
    if sc_start < 0:
        return questions

    text = text[sc_start:]
    lines = text.split("\n")
    current_q = None
    current_opts = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(k in line for k in ["查看答案", "模拟考场", "更多本套", "点此查看", "展开全文"]):
            continue

        # New question
        qm = re.match(r"^(\d{1,2})[.、．\\.]\s*(.+)", line)
        if qm:
            if current_q and len(current_q) > 5:
                if current_opts and len(current_opts) >= 2:
                    questions.append({"content": current_q.strip(), "question_type": "single_choice", "options": current_opts})
                elif "______" in current_q:
                    questions.append({"content": current_q.strip(), "question_type": "fill_blank", "options": []})
            current_q = qm.group(2).strip()
            current_opts = []
            # Check inline options
            inline = re.findall(r"([A-E])[.、．]\s*([^A-E.、．]+)", current_q)
            if inline and len(inline) >= 3:
                first = inline[0][0]
                for sep in [".", "、", " "]:
                    idx = current_q.find(f"{first}{sep}")
                    if idx > 0:
                        current_q = current_q[:idx].rstrip()
                        break
                current_opts = [o[1].strip() for o in inline]
            continue

        # Option
        om = re.match(r"^([A-E])[.、．]\s*(.+)", line)
        if om and current_q:
            current_opts.append(om.group(2).strip())
            continue

        # Inline options
        inline = re.findall(r"([A-E])[.、．]\s*([^A-E.、．]+)", line)
        if inline and len(inline) >= 3 and current_q:
            current_opts = [o[1].strip() for o in inline]
            continue

        # Content continuation
        if current_q and not current_opts and len(line) > 2 and len(line) < 120:
            current_q += " " + line

    # Last question
    if current_q and len(current_q) > 5 and current_opts and len(current_opts) >= 2:
        questions.append({"content": current_q.strip(), "question_type": "single_choice", "options": current_opts})

    return questions


def search_and_import():
    db = SessionLocal()
    province = db.query(Province).filter(Province.code == "13").first()
    province_id = province.id if province else None

    total_papers = 0
    total_questions = 0

    print(f"搜索源: {search_client.available_sources}")
    print(f"Tavily源数: {len(search_client.tavily_sources)}")
    print()

    for code, name in SUBJECTS:
        subject = db.query(Subject).filter(Subject.code == code).first()
        if not subject:
            continue

        print(f"\n=== {code} {name} ===")

        for year, month in SEARCH_PERIODS:
            # Skip if already imported via multi-search
            existing = db.query(PastPaper).filter(
                PastPaper.subject_id == subject.id,
                PastPaper.year == year,
                PastPaper.month == month,
                PastPaper.source.like("%多源搜索%"),
            ).first()
            if existing:
                print(f"  {year}年{month}月: 已存在，跳过")
                continue

            query = f"{year}年{month}月自考{code}{name}真题答案 单选题"
            results = search_client.unified_search(query, max_results=5)
            if not results:
                print(f"  {year}年{month}月: 无搜索结果")
                continue

            # Try to extract content from results
            questions = []
            source_url = ""
            for r in results:
                if not r.url or "bilibili" in r.url:
                    continue
                content = search_client.extract(r.url)
                if content and len(content) > 300:
                    questions = parse_questions(content)
                    if len(questions) >= 5:
                        source_url = r.url
                        break
                time.sleep(0.5)

            if not questions:
                print(f"  {year}年{month}月: 提取到0题")
                continue

            # Import to DB
            chapters = db.query(Chapter).filter(
                Chapter.subject_id == subject.id
            ).order_by(Chapter.order).all()

            question_ids = []
            new_count = 0
            for idx, q in enumerate(questions):
                existing_q = db.query(Question).filter(
                    Question.subject_id == subject.id,
                    Question.content == q["content"],
                ).first()
                if existing_q:
                    question_ids.append(existing_q.id)
                    continue

                chapter_id = chapters[idx % len(chapters)].id if chapters else None
                options_json = json.dumps(q["options"], ensure_ascii=False) if q["options"] else "[]"
                score = 2 if q["question_type"] == "single_choice" else 3

                new_q = Question(
                    subject_id=subject.id,
                    content=q["content"],
                    question_type=q["question_type"],
                    options=options_json,
                    answer="待核实",
                    explanation="真实自考真题（多源搜索获取），答案待核实",
                    year=year,
                    month=month,
                    chapter_id=chapter_id,
                    difficulty="medium",
                    frequency=8,
                    score=score,
                    source=f"真实真题-多源搜索-{year}年{month}月",
                )
                db.add(new_q)
                db.flush()
                question_ids.append(new_q.id)
                new_count += 1

            if question_ids:
                total_score = len([q for q in questions if q["question_type"] == "single_choice"]) * 2
                paper = PastPaper(
                    subject_id=subject.id,
                    name=f"{year}年{month}月 {subject.name} 真题（真实）",
                    year=year,
                    month=month,
                    province_id=province_id,
                    total_score=total_score or len(question_ids) * 2,
                    duration=150,
                    question_ids=question_ids,
                    paper_config={"source": "multi_search"},
                    source=f"真实真题-多源搜索-{source_url[:60]}",
                    is_published=True,
                )
                db.add(paper)
                total_papers += 1
                total_questions += new_count
                print(f"  {year}年{month}月: OK {len(question_ids)}题 (新增{new_count})")

            time.sleep(1.5)

    db.commit()
    db.close()
    print(f"\n{'='*50}")
    print(f"[OK] 多源搜索真题导入完成!")
    print(f"   新增试卷: {total_papers} 套")
    print(f"   新增题目: {total_questions} 道")


if __name__ == "__main__":
    search_and_import()
