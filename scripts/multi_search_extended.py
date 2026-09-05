# -*- coding: utf-8 -*-
"""Extended multi-search: cover more subjects and periods with answer extraction.

Usage:
    python -m scripts.multi_search_extended
"""

import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Major, MajorSubject, Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.search_client import MultiSearchClient

client = MultiSearchClient()

PERIODS = [
    (2025, 4),
    (2024, 10),
    (2024, 4),
    (2023, 10),
]


def parse_with_answers(text):
    """Parse questions with answers from articles."""
    questions = []
    blocks = re.split(r"\*\*\d{1,2}[.、．]", text)
    for block in blocks[1:]:
        lines = block.strip().split("\n")
        content = ""
        options = []
        answer = ""
        explanation = ""
        for line in lines:
            line = line.strip().rstrip("*")
            if not line:
                continue
            if line.startswith("【答案】"):
                answer = line.replace("【答案】", "").strip()
                continue
            if line.startswith("【解析】"):
                explanation = line.replace("【解析】", "").strip()
                continue
            opt_m = re.match(r"^([A-E])[.、．](.+)", line)
            if opt_m:
                options.append(opt_m.group(2).strip())
                continue
            if not options and not answer:
                content += line.replace("**", "").strip() + " "
        content = content.strip().rstrip("(）").strip()
        if content and len(content) > 5 and options and len(options) >= 2:
            questions.append({
                "content": content,
                "question_type": "single_choice" if len(options) == 4 else "multiple_choice",
                "options": options,
                "answer": answer or "待核实",
                "explanation": explanation,
            })
    return questions


def import_paper(db, subject, questions, year, month, province_id, source_url, has_answers):
    chapters = db.query(Chapter).filter(
        Chapter.subject_id == subject.id
    ).order_by(Chapter.order).all()
    qids = []
    new_cnt = 0
    for idx, q in enumerate(questions):
        eq = db.query(Question).filter(
            Question.subject_id == subject.id,
            Question.content == q["content"],
        ).first()
        if eq:
            if has_answers and eq.answer == "待核实" and q.get("answer") and q["answer"] != "待核实":
                eq.answer = q["answer"]
                eq.explanation = q.get("explanation") or eq.explanation
            qids.append(eq.id)
            continue
        cid = chapters[idx % len(chapters)].id if chapters else None
        nq = Question(
            subject_id=subject.id,
            content=q["content"],
            question_type=q["question_type"],
            options=json.dumps(q["options"], ensure_ascii=False),
            answer=q.get("answer") or "待核实",
            explanation=q.get("explanation") or "真实自考真题",
            year=year, month=month, chapter_id=cid, difficulty="medium",
            frequency=9, score=2,
            source=f"真实真题-多源搜索-{year}年{month}月",
        )
        db.add(nq)
        db.flush()
        qids.append(nq.id)
        new_cnt += 1
    if qids:
        label = "含答案" if has_answers else "部分"
        paper = PastPaper(
            subject_id=subject.id,
            name=f"{year}年{month}月 {subject.name} 真题（真实\xb7{label}）",
            year=year, month=month, province_id=province_id,
            total_score=len(qids) * 2, duration=150, question_ids=qids,
            paper_config={"source": "multi_search", "has_answers": has_answers},
            source=f"真实真题-多源搜索-{source_url[:60]}",
            is_published=True,
        )
        db.add(paper)
        return len(qids), new_cnt
    return 0, 0


def main():
    db = SessionLocal()
    province = db.query(Province).filter(Province.code == "13").first()
    province_id = province.id if province else None

    # Get all Hebei Univ subjects
    subject_ids = [
        r[0] for r in db.query(MajorSubject.subject_id)
        .join(Major, Major.id == MajorSubject.major_id)
        .filter(Major.school_id == 10).distinct().all()
    ]
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).order_by(Subject.code).all()

    print(f"搜索源: {client.available_sources}")
    print(f"科目数: {len(subjects)}, 考期数: {len(PERIODS)}")
    print()

    total_papers = 0
    total_questions = 0
    answered_count = 0

    for subject in subjects:
        code = subject.code
        name = subject.name

        for year, month in PERIODS:
            # Skip if already have multi-search paper
            existing = db.query(PastPaper).filter(
                PastPaper.subject_id == subject.id,
                PastPaper.year == year,
                PastPaper.month == month,
                PastPaper.source.like("%多源搜索%"),
            ).first()
            if existing:
                continue

            # Search
            query = f"{year}年{month}月自考 {name} 真题答案 【答案】"
            results = client.unified_search(query, max_results=3)

            questions = []
            source_url = ""
            for r in results:
                if "bilibili" in r.url:
                    continue
                # Prefer sohu/zhihu/shzkw articles that tend to have answers
                content = client.extract(r.url)
                if content and len(content) > 500:
                    questions = parse_with_answers(content)
                    if len(questions) >= 3:
                        source_url = r.url
                        break
                time.sleep(0.5)

            if not questions:
                continue

            has_answers = any(q.get("answer") and q["answer"] != "待核实" for q in questions)
            cnt, new = import_paper(db, subject, questions, year, month, province_id, source_url, has_answers)
            if cnt:
                total_papers += 1
                total_questions += new
                if has_answers:
                    answered_count += sum(1 for q in questions if q.get("answer") and q["answer"] != "待核实")
                print(f"  {code} {name} {year}年{month}月: {cnt}题(新增{new}) [答案:{has_answers}]")

            time.sleep(1.5)

    db.commit()
    db.close()
    print(f"\n{'='*50}")
    print(f"[OK] 扩展多源搜索完成!")
    print(f"   新增试卷: {total_papers} 套")
    print(f"   新增题目: {total_questions} 道")
    print(f"   含答案题目: {answered_count} 道")


if __name__ == "__main__":
    main()
