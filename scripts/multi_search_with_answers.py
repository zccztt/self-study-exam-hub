# -*- coding: utf-8 -*-
"""Import real papers with answers using multi-source search.

Finds papers from sohu and other sites that include answers and explanations.

Usage:
    python -m scripts.multi_search_with_answers
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


def parse_with_answers(text):
    """Parse questions with answers from articles (like sohu format)."""
    questions = []
    # Split by bold question numbers: **N. or **N、
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
    """Import parsed questions into DB."""
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
            # Update answer if we now have it and it was missing
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
            year=year,
            month=month,
            chapter_id=cid,
            difficulty="medium",
            frequency=9,
            score=2,
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
            year=year,
            month=month,
            province_id=province_id,
            total_score=len(qids) * 2,
            duration=150,
            question_ids=qids,
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

    print(f"搜索源: {search_client.available_sources}")
    print(f"Tavily源数: {len(search_client.tavily_sources)}")
    print()

    total_papers = 0
    total_questions = 0

    # Known good URLs with full answers
    KNOWN_URLS = [
        {"code": "03709", "year": 2025, "month": 4, "url": "https://www.sohu.com/a/883988308_121124333"},
        {"code": "00277", "year": 2026, "month": 4, "url": "https://www.sohu.com/a/1026090257_122367513"},
    ]

    # Import known URLs
    for t in KNOWN_URLS:
        subject = db.query(Subject).filter(Subject.code == t["code"]).first()
        if not subject:
            continue
        existing = db.query(PastPaper).filter(
            PastPaper.subject_id == subject.id,
            PastPaper.year == t["year"],
            PastPaper.month == t["month"],
            PastPaper.source.like("%多源搜索%"),
        ).first()
        if existing:
            print(f"{t['code']} {t['year']}年{t['month']}月: 已存在")
            continue

        content = search_client.extract(t["url"])
        if not content:
            print(f"{t['code']} {t['year']}年{t['month']}月: 提取失败")
            continue
        questions = parse_with_answers(content)
        has_answers = any(q.get("answer") and q["answer"] != "待核实" for q in questions)
        if questions:
            cnt, new = import_paper(db, subject, questions, t["year"], t["month"], province_id, t["url"], has_answers)
            if cnt:
                total_papers += 1
                total_questions += new
                print(f"OK {t['code']} {subject.name} {t['year']}年{t['month']}月: {cnt}题(新增{new}) [含答案:{has_answers}]")
        time.sleep(1)

    # Search for more with answers
    SEARCH_TARGETS = [
        ("03708", "中国近现代史纲要", 2025, 4),
        ("00315", "当代中国政治制度", 2025, 4),
        ("00107", "现代管理学", 2024, 10),
        ("00152", "组织行为学", 2024, 10),
        ("00320", "领导科学", 2024, 10),
        ("00230", "合同法", 2024, 10),
        ("02331", "数据结构", 2024, 10),
        ("04741", "计算机网络原理", 2024, 10),
    ]

    for code, name, year, month in SEARCH_TARGETS:
        subject = db.query(Subject).filter(Subject.code == code).first()
        if not subject:
            continue
        existing = db.query(PastPaper).filter(
            PastPaper.subject_id == subject.id,
            PastPaper.year == year,
            PastPaper.month == month,
            PastPaper.source.like("%多源搜索%"),
        ).first()
        if existing:
            print(f"{code} {year}年{month}月: 已存在")
            continue

        print(f"\n搜索 {code} {name} {year}年{month}月...")
        query = f"site:sohu.com {year}年{month}月自考{name}真题答案 解析"
        results = search_client.unified_search(query, max_results=5)

        questions = []
        source_url = ""
        for r in results:
            if "bilibili" in r.url:
                continue
            content = search_client.extract(r.url)
            if content and len(content) > 500:
                questions = parse_with_answers(content)
                if questions:
                    source_url = r.url
                    break
            time.sleep(0.5)

        if not questions:
            # Broader search
            query2 = f"{year}年{month}月 自考 {code} {name} 真题 答案 【答案】"
            results2 = search_client.unified_search(query2, max_results=3)
            for r in results2:
                if "bilibili" in r.url:
                    continue
                content = search_client.extract(r.url)
                if content and len(content) > 500:
                    questions = parse_with_answers(content)
                    if questions:
                        source_url = r.url
                        break
                time.sleep(0.5)

        if not questions:
            print(f"  未找到含答案的真题")
            continue

        has_answers = any(q.get("answer") and q["answer"] != "待核实" for q in questions)
        cnt, new = import_paper(db, subject, questions, year, month, province_id, source_url, has_answers)
        if cnt:
            total_papers += 1
            total_questions += new
            print(f"  OK: {cnt}题(新增{new}) [含答案:{has_answers}]")

        time.sleep(2)

    db.commit()
    db.close()
    print(f"\n{'='*50}")
    print(f"[OK] 多源搜索真题导入完成!")
    print(f"   新增试卷: {total_papers} 套")
    print(f"   新增题目: {total_questions} 道")


if __name__ == "__main__":
    main()
