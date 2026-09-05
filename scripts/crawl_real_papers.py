# -*- coding: utf-8 -*-
"""Crawler for zikaosw.cn real exam papers using Playwright.

Extracts actual self-study exam questions from zikaosw.cn.
Handles JS anti-bot protection via headless browser.

Usage:
    python -m scripts.crawl_real_papers
    python -m scripts.crawl_real_papers --subject 00277
    python -m scripts.crawl_real_papers --list-subjects
"""

import argparse
import json
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from playwright.sync_api import sync_playwright, Page, Browser

logger = logging.getLogger(__name__)

# Subject code -> zikaosw site subject ID mapping
# Found from: https://www.zikaosw.cn/lnzt/subject-{site_id}.html
SUBJECT_SITE_IDS = {
    "00277": 280,   # 行政管理学
    "03708": 9,     # 中国近现代史纲要 (mapped as 15043/03708)
    "03709": 702,   # 马克思主义基本原理概论
    "00015": 722,   # 英语(二)
    "02331": 1170,  # 数据结构
    "04741": 1166,  # 计算机网络原理
    "00315": None,  # 当代中国政治制度 - need to find
    "02326": None,  # 操作系统 - need to find
    "04735": None,  # 数据库系统原理 - need to find
}

# Paper listing URL pattern
SUBJECT_LIST_URL = "https://www.zikaosw.cn/lnzt/subject-{site_id}.html"


class ZikaoPaperCrawler:
    """Crawls real exam papers from zikaosw.cn using Playwright."""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self._pw = None

    def start(self):
        """Launch browser."""
        from playwright.sync_api import sync_playwright
        self._pw = sync_playwright().start()
        self.browser = self._pw.chromium.launch(headless=self.headless)
        self.page = self.browser.new_page()
        self.page.set_extra_http_headers({
            "Accept-Language": "zh-CN,zh;q=0.9",
        })

    def stop(self):
        """Close browser."""
        if self.browser:
            self.browser.close()
        if self._pw:
            self._pw.stop()

    def get_paper_links(self, site_id: int) -> List[Dict[str, str]]:
        """Get list of available papers for a subject."""
        url = SUBJECT_LIST_URL.format(site_id=site_id)
        self.page.goto(url, timeout=30000)
        self.page.wait_for_load_state("networkidle", timeout=15000)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.page.content(), "html.parser")

        papers = []
        for a in soup.find_all("a", href=True):
            text = a.get_text(strip=True)
            href = a["href"]
            # Match pattern like "2024年10月自考00277行政管理学历年真题及答案"
            match = re.match(r"(\d{4})年(\d{1,2})月自考.*真题", text)
            if match:
                year = int(match.group(1))
                month = int(match.group(2))
                if not href.startswith("http"):
                    href = "https://www.zikaosw.cn" + href
                papers.append({
                    "year": year,
                    "month": month,
                    "title": text,
                    "url": href,
                })

        # Deduplicate and sort
        seen = set()
        unique_papers = []
        for p in papers:
            key = (p["year"], p["month"])
            if key not in seen:
                seen.add(key)
                unique_papers.append(p)
        unique_papers.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
        return unique_papers

    def crawl_paper(self, url: str) -> List[Dict[str, Any]]:
        """Crawl a single paper page and extract questions."""
        self.page.goto(url, timeout=30000)
        self.page.wait_for_load_state("networkidle", timeout=15000)

        # Try to dismiss any overlay/popup
        try:
            close_btns = self.page.query_selector_all(".close, .mask-close, [class*=close]")
            for btn in close_btns:
                try:
                    btn.click(timeout=2000)
                except:
                    pass
        except:
            pass

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(self.page.content(), "html.parser")
        body_text = soup.get_text()

        # Extract questions
        questions = self._parse_questions(body_text)
        return questions

    def _parse_questions(self, text: str) -> List[Dict[str, Any]]:
        """Parse question text into structured data."""
        questions = []

        # Split by question number patterns: "1、" or "1." or "1．"
        # Find all question starts
        pattern = re.compile(r'(?:^|\n)\s*(\d{1,2})[、.．]\s*(.+?)(?=\n\s*\d{1,2}[、.．]|\n\s*(?:查看答案|更多本套)|$)', re.DOTALL)

        matches = pattern.findall(text)

        for num_str, q_text in matches:
            q_text = q_text.strip()
            if not q_text or len(q_text) < 10:
                continue

            question = self._parse_single_question(int(num_str), q_text)
            if question:
                questions.append(question)

        return questions

    def _parse_single_question(self, num: int, text: str) -> Optional[Dict[str, Any]]:
        """Parse a single question text block."""
        # Remove "查看答案" and "模拟考场" markers
        text = re.sub(r'查看答案.*?模拟考场', '', text, flags=re.DOTALL).strip()
        text = text.replace('查看答案', '').replace('模拟考场', '').strip()

        # Try to split content from options
        # Options pattern: A.xxx B.xxx or A、xxx B、xxx
        option_pattern = re.compile(r'\n?\s*([A-F])[.、．]\s*(.+?)(?=\s*[B-F][.、．]|$)', re.DOTALL)
        options_matches = option_pattern.findall(text)

        if options_matches and len(options_matches) >= 2:
            # This is a choice question
            # Extract content (everything before first option)
            first_opt = text.find(options_matches[0][1].strip()[:10])
            # Find where options start
            opt_start = re.search(r'\s*A[.、．]', text)
            if opt_start:
                content = text[:opt_start.start()].strip()
            else:
                content = text.split('\n')[0].strip()

            options = [opt_text.strip() for _, opt_text in options_matches]

            # Determine if single or multiple choice
            q_type = "single_choice"  # default, will be corrected when answer is known

            return {
                "number": num,
                "content": content,
                "question_type": q_type,
                "options": options,
                "answer": None,  # Answer hidden behind paywall
                "explanation": None,
            }
        else:
            # Non-choice question (fill blank, short answer, essay)
            content = text.strip()
            if "______" in content or "____" in content:
                q_type = "fill_blank"
            elif len(content) < 100:
                q_type = "fill_blank"
            else:
                q_type = "short_answer"

            return {
                "number": num,
                "content": content,
                "question_type": q_type,
                "options": [],
                "answer": None,
                "explanation": None,
            }


def crawl_subject(subject_code: str, output_dir: Path, max_papers: int = 5):
    """Crawl papers for a specific subject."""
    site_id = SUBJECT_SITE_IDS.get(subject_code)
    if not site_id:
        print(f"  ERROR: No site ID mapping for subject {subject_code}")
        return []

    crawler = ZikaoPaperCrawler(headless=True)
    crawler.start()

    try:
        print(f"  Getting paper list for {subject_code} (site_id={site_id})...")
        papers = crawler.get_paper_links(site_id)
        print(f"  Found {len(papers)} papers")

        results = []
        for paper_info in papers[:max_papers]:
            print(f"    Crawling: {paper_info['title']}...")
            try:
                questions = crawler.crawl_paper(paper_info["url"])
                paper_info["questions"] = questions
                paper_info["question_count"] = len(questions)
                results.append(paper_info)
                print(f"      Extracted {len(questions)} questions")
            except Exception as e:
                print(f"      ERROR: {e}")
            time.sleep(2)  # Rate limiting

        # Save to JSON
        output_file = output_dir / f"{subject_code}_papers.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {output_file}")

        return results

    finally:
        crawler.stop()


def main():
    parser = argparse.ArgumentParser(description="Crawl real exam papers from zikaosw.cn")
    parser.add_argument("--subject", type=str, help="Subject code to crawl (e.g. 00277)")
    parser.add_argument("--all", action="store_true", help="Crawl all mapped subjects")
    parser.add_argument("--list-subjects", action="store_true", help="List available subjects")
    parser.add_argument("--max-papers", type=int, default=3, help="Max papers per subject")
    parser.add_argument("--output", type=str, default="data/real_papers", help="Output directory")
    args = parser.parse_args()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.list_subjects:
        print("Available subjects with site IDs:")
        for code, sid in SUBJECT_SITE_IDS.items():
            status = f"site_id={sid}" if sid else "NOT MAPPED"
            print(f"  {code}: {status}")
        return

    subjects_to_crawl = []
    if args.subject:
        subjects_to_crawl = [args.subject]
    elif args.all:
        subjects_to_crawl = [k for k, v in SUBJECT_SITE_IDS.items() if v is not None]
    else:
        # Default: crawl 行政管理学
        subjects_to_crawl = ["00277"]

    print(f"Crawling {len(subjects_to_crawl)} subjects...")
    print()

    for code in subjects_to_crawl:
        print(f"=== Subject {code} ===")
        crawl_subject(code, output_dir, max_papers=args.max_papers)
        print()

    print("[OK] Crawl complete!")


if __name__ == "__main__":
    main()
