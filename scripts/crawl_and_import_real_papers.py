# -*- coding: utf-8 -*-
"""Batch crawl real papers for all 60 subjects and import to DB.

Usage:
    python -m scripts.crawl_and_import_real_papers
"""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Province
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject

BASE_URL = "https://www.zikaosw.cn"

# Load site ID mapping
MAPPING_FILE = Path(__file__).resolve().parent.parent / "data" / "real_papers" / "subject_site_ids.json"
with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    SITE_IDS = json.load(f)


def parse_questions_from_text(text):
    """Parse question text into structured data."""
    questions = []
    lines = text.split("\n")
    current_q = None
    current_options = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        q_match = re.match(r"^(\d{1,2})[、.．]\s*(.+)", line)
        if q_match:
            if current_q and len(current_q) > 5:
                q_data = finalize_question(current_q, current_options)
                if q_data:
                    questions.append(q_data)
            current_q = q_match.group(2).strip()
            current_options = []
            continue

        opt_match = re.match(r"^([A-F])[.、．]\s*(.+)", line)
        if opt_match and current_q:
            current_options.append(opt_match.group(2).strip())
            continue

        if any(k in line for k in ["查看答案", "模拟考场", "更多本套"]):
            continue

        if current_q and not current_options and len(line) > 3 and len(line) < 100:
            current_q += line

    if current_q and len(current_q) > 5:
        q_data = finalize_question(current_q, current_options)
        if q_data:
            questions.append(q_data)

    return questions


def finalize_question(content, options):
    """Create question dict from parsed content and options."""
    content = content.strip()
    content = re.sub(r"查看答案.*", "", content).strip()
    content = re.sub(r"模拟考场.*", "", content).strip()

    if len(content) < 5:
        return None

    if options and len(options) >= 2:
        return {
            "content": content,
            "question_type": "single_choice",
            "options": options,
            "answer": None,
            "explanation": None,
        }
    elif "______" in content or "____" in content:
        return {
            "content": content,
            "question_type": "fill_blank",
            "options": [],
            "answer": None,
            "explanation": None,
        }
    return None


def crawl_all():
    """Crawl latest paper for each subject and import real questions."""
    db = SessionLocal()
    province = db.query(Province).filter(Province.code == "13").first()
    province_id = province.id if province else None

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        total_papers = 0
        total_questions = 0
        errors = 0

        codes = sorted(SITE_IDS.keys())
        print(f"Crawling {len(codes)} subjects...")
        print()

        for code in codes:
            site_id = SITE_IDS[code]
            subject = db.query(Subject).filter(Subject.code == code).first()
            if not subject:
                print(f"  SKIP {code}: not in DB")
                continue

            try:
                # Step 1: Get paper list
                list_url = f"{BASE_URL}/lnzt/subject-{site_id}.html"
                page.goto(list_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
                soup = BeautifulSoup(page.content(), "html.parser")

                paper_links = []
                for a in soup.find_all("a", href=True):
                    text = a.get_text(strip=True)
                    href = a["href"]
                    m = re.match(r"(\d{4})年(\d{1,2})月自考.*真题", text)
                    if m:
                        yr, mo = int(m.group(1)), int(m.group(2))
                        full_url = href if href.startswith("http") else BASE_URL + href
                        paper_links.append((yr, mo, full_url, text))

                if not paper_links:
                    print(f"  SKIP {code} {subject.name}: no papers found")
                    continue

                paper_links.sort(key=lambda x: (x[0], x[1]), reverse=True)
                # Try papers from newest to oldest until we find one with content
                yr, mo, paper_url, title = None, None, None, None
                for pl in paper_links:
                    # Skip 2026年4月 (too recent, likely no content yet)
                    if pl[0] >= 2026 and pl[1] >= 4:
                        continue
                    yr, mo, paper_url, title = pl
                    break
                if not yr:
                    print(f"  SKIP {code} {subject.name}: no suitable paper period")
                    continue

                # Check existing real paper
                existing = db.query(PastPaper).filter(
                    PastPaper.subject_id == subject.id,
                    PastPaper.source.like("%真实真题%"),
                ).first()
                if existing:
                    print(f"  SKIP {code} {subject.name}: real paper exists")
                    continue

                # Step 2: Crawl the paper page
                page.goto(paper_url, timeout=30000)
                page.wait_for_load_state("networkidle", timeout=15000)
                soup2 = BeautifulSoup(page.content(), "html.parser")
                body_text = soup2.get_text()

                # Step 3: Parse questions
                questions = parse_questions_from_text(body_text)
                if not questions:
                    print(f"  SKIP {code} {subject.name}: no questions parsed from {yr}年{mo}月")
                    continue

                # Step 4: Import to DB
                chapters = db.query(Chapter).filter(
                    Chapter.subject_id == subject.id
                ).order_by(Chapter.order).all()

                question_ids = []
                new_q_count = 0
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

                    new_question = Question(
                        subject_id=subject.id,
                        content=q["content"],
                        question_type=q["question_type"],
                        options=options_json,
                        answer=q.get("answer") or "待核实",
                        explanation=q.get("explanation") or "真实自考真题，答案待核实",
                        year=yr,
                        month=mo,
                        chapter_id=chapter_id,
                        difficulty="medium",
                        frequency=5,
                        score=2 if q["question_type"] == "single_choice" else 3,
                        source=f"真实真题-{yr}年{mo}月自考",
                    )
                    db.add(new_question)
                    db.flush()
                    question_ids.append(new_question.id)
                    new_q_count += 1

                if question_ids:
                    total_score = sum(2 if q["question_type"] == "single_choice" else 3 for q in questions)
                    paper = PastPaper(
                        subject_id=subject.id,
                        name=f"{yr}年{mo}月 {subject.name} 真题（真实）",
                        year=yr,
                        month=mo,
                        province_id=province_id,
                        total_score=total_score,
                        duration=150,
                        question_ids=question_ids,
                        paper_config={"source": "zikaosw.cn", "partial": True},
                        source=f"真实真题-zikaosw.cn-{yr}年{mo}月",
                        is_published=True,
                    )
                    db.add(paper)
                    total_papers += 1
                    total_questions += new_q_count
                    print(f"  OK {code} {subject.name}: {yr}年{mo}月 {len(question_ids)}题 (新增{new_q_count})")

            except Exception as e:
                errors += 1
                print(f"  ERR {code} {subject.name}: {type(e).__name__}: {str(e)[:60]}")

            time.sleep(1.5)

        browser.close()

    db.commit()
    db.close()
    print()
    print(f"[OK] 真题爬取完成!")
    print(f"   新增真题试卷: {total_papers} 套")
    print(f"   新增真题题目: {total_questions} 道")
    print(f"   错误: {errors}")


if __name__ == "__main__":
    crawl_all()
