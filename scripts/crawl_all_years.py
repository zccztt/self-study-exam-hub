# -*- coding: utf-8 -*-
"""Comprehensive crawl: fetch ALL available papers from 2021-2026 for Hebei Univ subjects.

Combines:
1. Playwright crawling of zikaosw.cn (gets all listed paper periods)
2. Tavily search for sohu.com articles (gets fuller content)

Usage:
    python -m scripts.crawl_all_years
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx
from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup

from backend.database import SessionLocal
from backend.models.chapter import Chapter
from backend.models.enrollment import Province, Major, MajorSubject
from backend.models.past_paper import PastPaper
from backend.models.question import Question
from backend.models.subject import Subject
from backend.services.search_provider_service import SearchProviderService

BASE_URL = "https://www.zikaosw.cn"

# Load Tavily credentials from DB; fall back to environment variable
def _load_tavily_config():
    try:
        db = SessionLocal()
        sources = SearchProviderService(db).get_tavily_sources()
        db.close()
        if sources:
            return sources[0]["key"], sources[0]["url"]
    except Exception:
        pass
    env_key = os.environ.get("TAVILY_API_KEY")
    if env_key:
        return env_key, os.environ.get("TAVILY_BASE_URL", "https://api.tavily.com")
    return None, None

TAVILY_KEY, TAVILY_URL = _load_tavily_config()
if not TAVILY_KEY:
    print("[ERROR] Tavily API key not found. Configure a Tavily search provider in the DB or set TAVILY_API_KEY env var.")
    sys.exit(1)

MAPPING_FILE = Path(__file__).resolve().parent.parent / "data" / "real_papers" / "subject_site_ids.json"
with open(MAPPING_FILE, "r", encoding="utf-8") as f:
    SITE_IDS = json.load(f)

MIN_YEAR = 2021
MAX_YEAR = 2026


def tavily_search(query):
    payload = {
        "api_key": TAVILY_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": 5,
        "include_answer": False,
    }
    try:
        r = httpx.post(f"{TAVILY_URL}/search", json=payload, timeout=30)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception:
        pass
    return []


def tavily_extract(urls):
    payload = {"api_key": TAVILY_KEY, "urls": urls}
    try:
        r = httpx.post(f"{TAVILY_URL}/extract", json=payload, timeout=30)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception:
        pass
    return []


def parse_questions_from_page(body_text):
    """Parse questions from page text (zikaosw style)."""
    questions = []
    lines = body_text.split("\n")
    current_num = None
    current_content = ""
    current_options = []

    for line in lines:
        line = line.strip()
        if not line:
            continue
        if any(k in line for k in ["查看答案", "模拟考场", "更多本套", "点此查看"]):
            continue

        q_match = re.match(r"^(\d{1,2})[、.．]\s*(.+)", line)
        if q_match:
            if current_num and current_content and len(current_content) > 5:
                questions.append(_make_q(current_content, current_options))
            current_num = int(q_match.group(1))
            current_content = q_match.group(2).strip()
            current_options = []
            continue

        opt_match = re.match(r"^([A-F])[.、．]\s*(.+)", line)
        if opt_match and current_num:
            current_options.append(opt_match.group(2).strip())
            continue

        if current_num and not current_options and len(line) > 2 and len(line) < 120:
            current_content += " " + line

    if current_num and current_content and len(current_content) > 5:
        questions.append(_make_q(current_content, current_options))

    return [q for q in questions if q is not None]


def parse_exam_content_tavily(text):
    """Parse full exam paper text from Tavily extract."""
    questions = []
    sc_start = text.find("单项选择题")
    mc_start = text.find("多项选择题")

    if sc_start < 0:
        return parse_questions_from_page(text)

    sc_end = mc_start if mc_start > sc_start else len(text)
    sc_text = text[sc_start:sc_end]
    questions.extend(_parse_section(sc_text, "single_choice"))

    if mc_start > 0:
        next_sec = len(text)
        for marker in ["简答题", "论述题", "填空题", "名词解释", "三、", "四、"]:
            idx = text.find(marker, mc_start + 10)
            if 0 < idx < next_sec:
                next_sec = idx
        mc_text = text[mc_start:next_sec]
        questions.extend(_parse_section(mc_text, "multiple_choice"))

    return [q for q in questions if q and len(q.get("content", "")) >= 5 and len(q.get("options", [])) >= 2]


def _parse_section(text, qtype):
    questions = []
    lines = text.split("\n")
    current_num = None
    current_content = ""
    current_options = []

    max_letter = "E" if qtype == "multiple_choice" else "D"

    for line in lines:
        line = line.strip()
        if not line:
            continue

        q_match = re.match(r"^(\d{1,2})[.、．\s]+(.+)", line)
        if q_match:
            if current_num and current_content:
                q = _make_q(current_content, current_options, qtype)
                if q:
                    questions.append(q)
            current_num = int(q_match.group(1))
            rest = q_match.group(2).strip()
            pat = r"([A-" + max_letter + r"])[.、．]\s*([^A-" + max_letter + r".、．]+)"
            inline = re.findall(pat, rest)
            if inline and len(inline) >= 3:
                first = inline[0][0]
                for sep in [".", "、", " "]:
                    idx = rest.find(f"{first}{sep}")
                    if idx > 0:
                        current_content = rest[:idx].rstrip()
                        break
                else:
                    current_content = rest
                current_options = [o[1].strip() for o in inline]
            else:
                current_content = rest
                current_options = []
            continue

        opt_match = re.match(r"^([A-" + max_letter + r"])[.、．]\s*(.+)", line)
        if opt_match and current_num:
            current_options.append(opt_match.group(2).strip())
            continue

        pat = r"([A-" + max_letter + r"])[.、．]\s*([^A-" + max_letter + r".、．]+)"
        inline = re.findall(pat, line)
        if inline and len(inline) >= 3 and current_num:
            current_options = [o[1].strip() for o in inline]
            continue

        if current_num and not current_options and len(line) > 2:
            current_content += " " + line

    if current_num and current_content:
        q = _make_q(current_content, current_options, qtype)
        if q:
            questions.append(q)

    return questions


def _make_q(content, options, qtype=None):
    content = content.strip()
    content = re.sub(r"查看答案.*", "", content).strip()
    content = re.sub(r"模拟考场.*", "", content).strip()
    if len(content) < 5:
        return None
    if options and len(options) >= 2:
        if qtype is None:
            qtype = "single_choice"
        return {"content": content, "question_type": qtype, "options": options, "answer": None}
    elif "______" in content or "____" in content:
        return {"content": content, "question_type": "fill_blank", "options": [], "answer": None}
    return None


def import_questions(db, subject, questions, year, month, province_id, source_tag):
    """Import parsed questions to DB and create PastPaper record."""
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
        score = 2 if q["question_type"] == "single_choice" else 4

        new_q = Question(
            subject_id=subject.id,
            content=q["content"],
            question_type=q["question_type"],
            options=options_json,
            answer=q.get("answer") or "待核实",
            explanation="真实自考真题，答案待核实",
            year=year,
            month=month,
            chapter_id=chapter_id,
            difficulty="medium",
            frequency=8,
            score=score,
            source=f"真实真题-{source_tag}-{year}年{month}月",
        )
        db.add(new_q)
        db.flush()
        question_ids.append(new_q.id)
        new_count += 1

    if question_ids:
        total_score = sum(2 if q["question_type"] == "single_choice" else 4 for q in questions)
        paper = PastPaper(
            subject_id=subject.id,
            name=f"{year}年{month}月 {subject.name} 真题（真实）",
            year=year,
            month=month,
            province_id=province_id,
            total_score=total_score,
            duration=150,
            question_ids=question_ids,
            paper_config={"source": source_tag, "partial": len(questions) < 36},
            source=f"真实真题-{source_tag}-{year}年{month}月",
            is_published=True,
        )
        db.add(paper)
        return len(question_ids), new_count

    return 0, 0


def crawl_all_years():
    db = SessionLocal()
    province = db.query(Province).filter(Province.code == "13").first()
    province_id = province.id if province else None

    # Get Hebei Univ subject IDs
    subject_ids = [
        r[0] for r in db.query(MajorSubject.subject_id)
        .join(Major, Major.id == MajorSubject.major_id)
        .filter(Major.school_id == 10).distinct().all()
    ]
    subjects = db.query(Subject).filter(Subject.id.in_(subject_ids)).order_by(Subject.code).all()
    print(f"Processing {len(subjects)} subjects, years {MIN_YEAR}-{MAX_YEAR}")
    print()

    total_papers = 0
    total_questions = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for subject in subjects:
            code = subject.code
            site_id = SITE_IDS.get(code)
            if not site_id:
                continue

            print(f"\n--- {code} {subject.name} ---")

            try:
                # Get all paper links from zikaosw
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
                        if MIN_YEAR <= yr <= MAX_YEAR:
                            full_url = href if href.startswith("http") else BASE_URL + href
                            paper_links.append((yr, mo, full_url))

                # Deduplicate
                seen = set()
                unique_links = []
                for yr, mo, url in paper_links:
                    if (yr, mo) not in seen:
                        seen.add((yr, mo))
                        unique_links.append((yr, mo, url))
                unique_links.sort(key=lambda x: (x[0], x[1]), reverse=True)

                if not unique_links:
                    print(f"  No papers found on zikaosw")
                    continue

                print(f"  Found {len(unique_links)} periods: {[(y,m) for y,m,_ in unique_links]}")

                for yr, mo, paper_url in unique_links:
                    # Check if already have real paper for this subject+year+month
                    existing = db.query(PastPaper).filter(
                        PastPaper.subject_id == subject.id,
                        PastPaper.year == yr,
                        PastPaper.month == mo,
                        PastPaper.source.like("%真实真题%"),
                    ).first()
                    if existing:
                        continue

                    # Try crawling from zikaosw
                    try:
                        page.goto(paper_url, timeout=30000)
                        page.wait_for_load_state("networkidle", timeout=15000)
                        soup2 = BeautifulSoup(page.content(), "html.parser")
                        body_text = soup2.get_text()
                        questions = parse_questions_from_page(body_text)
                    except Exception:
                        questions = []

                    # If zikaosw didn't work well, try Tavily for sohu articles
                    if len(questions) < 5:
                        results = tavily_search(f"site:sohu.com {yr}年{mo}月自考{code}{subject.name}真题 选择题")
                        for res in results:
                            content = res.get("content", "")
                            url = res.get("url", "")
                            if "选择" in content or "备选项" in content:
                                extracted = tavily_extract([url])
                                if extracted:
                                    raw = extracted[0].get("raw_content", "") or extracted[0].get("content", "")
                                    if len(raw) > 200:
                                        questions = parse_exam_content_tavily(raw)
                                        if questions:
                                            break
                        time.sleep(1)

                    if not questions:
                        continue

                    q_count, new_count = import_questions(
                        db, subject, questions, yr, mo, province_id, "crawl"
                    )
                    if q_count > 0:
                        total_papers += 1
                        total_questions += new_count
                        print(f"  {yr}年{mo}月: {q_count}题 (新增{new_count})")

                    time.sleep(1)

            except Exception as e:
                print(f"  ERROR: {type(e).__name__}: {str(e)[:60]}")

            time.sleep(1)

        browser.close()

    db.commit()
    db.close()

    print(f"\n{'='*50}")
    print(f"[OK] 全量真题爬取完成!")
    print(f"   新增真题试卷: {total_papers} 套")
    print(f"   新增真题题目: {total_questions} 道")


if __name__ == "__main__":
    crawl_all_years()
