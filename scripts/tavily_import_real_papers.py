# -*- coding: utf-8 -*-
"""Search and import real exam papers via Tavily API.

Searches public websites (sohu, zhihu, etc.) for actual self-exam papers
and imports questions into the database.

Usage:
    python -m scripts.tavily_import_real_papers
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
from backend.services.search_client import MultiSearchClient

# Use unified multi-search client
client = MultiSearchClient()

SUBJECTS_TO_SEARCH = [
    ("00277", "行政管理学"),
    ("03708", "中国近现代史纲要"),
    ("03709", "马克思主义基本原理概论"),
    ("00315", "当代中国政治制度"),
    ("00318", "公共政策"),
    ("00320", "领导科学"),
    ("02331", "数据结构"),
    ("04741", "计算机网络原理"),
    ("00152", "组织行为学"),
    ("00107", "现代管理学"),
]


def tavily_search(query):
    """Search using unified multi-search client."""
    results = client.unified_search(query, max_results=5)
    return [{"title": r.title, "url": r.url, "content": r.content} for r in results]


def tavily_extract(urls):
    """Extract content from URLs using unified client."""
    results = []
    for url in urls:
        content = client.extract(url)
        if content:
            results.append({"raw_content": content, "content": content})
    return results


def parse_exam_content(text):
    """Parse exam paper text into structured questions."""
    questions = []

    sc_start = text.find("单项选择题")
    mc_start = text.find("多项选择题")

    if sc_start < 0:
        return questions

    # Single choice section
    sc_end = mc_start if mc_start > sc_start else len(text)
    sc_text = text[sc_start:sc_end]
    questions.extend(_parse_choice_section(sc_text, "single_choice"))

    # Multiple choice section
    if mc_start > 0:
        # Find end of multi-choice (next section)
        next_section = len(text)
        for marker in ["简答题", "论述题", "填空题", "名词解释", "三、", "四、"]:
            idx = text.find(marker, mc_start + 10)
            if idx > 0 and idx < next_section:
                next_section = idx
        mc_text = text[mc_start:next_section]
        questions.extend(_parse_choice_section(mc_text, "multiple_choice"))

    return [q for q in questions if len(q["content"]) >= 5 and len(q["options"]) >= 2]


def _parse_choice_section(text, qtype):
    """Parse a choice question section."""
    questions = []
    lines = text.split("\n")
    current_num = None
    current_content = ""
    current_options = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # New question
        q_match = re.match(r"^(\d{1,2})[.、．\s]+(.+)", line)
        if q_match:
            if current_num and current_content:
                questions.append({
                    "number": current_num,
                    "content": current_content.strip(),
                    "question_type": qtype,
                    "options": current_options,
                    "answer": None,
                })
            current_num = int(q_match.group(1))
            rest = q_match.group(2).strip()

            # Check inline options
            max_letter = "D" if qtype == "single_choice" else "E"
            opt_pattern = r"([A-" + max_letter + r"])[.、．]\s*([^A-" + max_letter + r".、．]+)"
            inline_opts = re.findall(opt_pattern, rest)
            if inline_opts and len(inline_opts) >= 3:
                first_opt = inline_opts[0][0]
                opt_idx = rest.find(f"{first_opt}.")
                if opt_idx < 0:
                    opt_idx = rest.find(f"{first_opt}、")
                if opt_idx < 0:
                    opt_idx = rest.find(f"{first_opt} ")
                current_content = rest[:opt_idx].rstrip() if opt_idx > 0 else rest
                current_options = [o[1].strip() for o in inline_opts]
            else:
                current_content = rest
                current_options = []
            continue

        # Option line
        max_letter = "D" if qtype == "single_choice" else "E"
        opt_match = re.match(r"^([A-" + max_letter + r"])[.、．]\s*(.+)", line)
        if opt_match and current_num:
            current_options.append(opt_match.group(2).strip())
            continue

        # Inline options on a single line
        opt_pattern = r"([A-" + max_letter + r"])[.、．]\s*([^A-" + max_letter + r".、．]+)"
        inline_opts = re.findall(opt_pattern, line)
        if inline_opts and len(inline_opts) >= 3 and current_num:
            current_options = [o[1].strip() for o in inline_opts]
            continue

        # Content continuation
        if current_num and not current_options and len(line) > 2:
            current_content += " " + line

    # Last question
    if current_num and current_content:
        questions.append({
            "number": current_num,
            "content": current_content.strip(),
            "question_type": qtype,
            "options": current_options,
            "answer": None,
        })

    return questions


def search_and_import():
    db = SessionLocal()
    province = db.query(Province).filter(Province.code == "13").first()
    province_id = province.id if province else None

    total_papers = 0
    total_questions = 0

    for code, name in SUBJECTS_TO_SEARCH:
        subject = db.query(Subject).filter(Subject.code == code).first()
        if not subject:
            print(f"  SKIP {code}: not in DB")
            continue

        print(f"\n=== {code} {name} ===")

        # Search
        queries = [
            f"site:sohu.com 自考{code}{name}真题 单项选择题 备选项",
            f"自考{code}{name} 2025 OR 2026 真题答案 选择题 A B C D",
        ]

        found_url = None
        for query in queries:
            results = tavily_search(query)
            for res in results:
                content = res.get("content", "")
                url = res.get("url", "")
                if ("单项选择" in content or "备选项" in content) and (code in url or code in content or name[:4] in content):
                    found_url = url
                    print(f"  Found: {url[:80]}")
                    break
            if found_url:
                break
            time.sleep(1)

        if not found_url:
            print(f"  No paper URL found")
            continue

        # Extract full content
        extracted = tavily_extract([found_url])
        if not extracted:
            print(f"  Failed to extract content")
            continue

        raw_content = extracted[0].get("raw_content", "") or extracted[0].get("content", "")
        if len(raw_content) < 200:
            print(f"  Content too short ({len(raw_content)} chars)")
            continue

        # Determine year/month
        year_match = re.search(r"(202[3-6])年(\d{1,2})月", raw_content[:500])
        if year_match:
            year = int(year_match.group(1))
            month = int(year_match.group(2))
        else:
            year, month = 2025, 10

        # Parse questions
        questions = parse_exam_content(raw_content)
        print(f"  Parsed {len(questions)} questions from {year}年{month}月")

        if not questions:
            continue

        # Check existing
        existing = db.query(PastPaper).filter(
            PastPaper.subject_id == subject.id,
            PastPaper.source.like("%Tavily%"),
        ).first()
        if existing:
            print(f"  Already imported, skipping")
            continue

        # Import
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
            options_json = json.dumps(q["options"], ensure_ascii=False)
            score = 2 if q["question_type"] == "single_choice" else 4

            new_q = Question(
                subject_id=subject.id,
                content=q["content"],
                question_type=q["question_type"],
                options=options_json,
                answer="待核实",
                explanation="真实自考真题（来源：公开网络），答案待核实",
                year=year,
                month=month,
                chapter_id=chapter_id,
                difficulty="medium",
                frequency=8,
                score=score,
                source=f"真实真题-Tavily-{year}年{month}月",
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
                paper_config={"source": "Tavily", "partial": len(questions) < 36},
                source=f"真实真题-Tavily-{found_url[:60]}",
                is_published=True,
            )
            db.add(paper)
            total_papers += 1
            total_questions += new_count
            print(f"  OK: imported {len(question_ids)} questions (new: {new_count})")

        time.sleep(2)

    db.commit()
    db.close()

    print(f"\n[OK] Tavily真题搜索导入完成!")
    print(f"   新增试卷: {total_papers} 套")
    print(f"   新增题目: {total_questions} 道")


if __name__ == "__main__":
    search_and_import()
