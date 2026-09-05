# -*- coding: utf-8 -*-
"""爬取河北省教育考试院自考日程信息。

来源: https://zk.hebeea.edu.cn/

尝试从河北省自考信息系统首页和公告页面提取:
- 报名时间
- 考试时间
- 成绩查询时间

如果网站反爬或内容变更，回退到手工维护的静态数据。

Usage:
    python -m scripts.crawl_exam_schedule
    python -m scripts.crawl_exam_schedule --dry-run
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import date, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    import requests
    from bs4 import BeautifulSoup
    HAS_DEPS = True
except ImportError:
    HAS_DEPS = False

from backend.database import SessionLocal
from backend.models.exam_schedule import ExamSchedule

SOURCE_URL = "https://zk.hebeea.edu.cn/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml",
}

# ------------------------------------------------------------------
# 静态兜底数据 (当爬取失败时使用)
# ------------------------------------------------------------------

FALLBACK_SCHEDULES = [
    {
        "exam_period": "2025年4月",
        "register_start": "2025-01-05",
        "register_end": "2025-01-10",
        "exam_start": "2025-04-12",
        "exam_end": "2025-04-13",
        "result_date": "2025-05-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
    {
        "exam_period": "2025年10月",
        "register_start": "2025-06-10",
        "register_end": "2025-06-15",
        "exam_start": "2025-10-25",
        "exam_end": "2025-10-26",
        "result_date": "2025-11-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
    {
        "exam_period": "2026年4月",
        "register_start": "2026-01-05",
        "register_end": "2026-01-10",
        "exam_start": "2026-04-11",
        "exam_end": "2026-04-12",
        "result_date": "2026-05-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
    {
        "exam_period": "2026年10月",
        "register_start": "2026-06-10",
        "register_end": "2026-06-15",
        "exam_start": "2026-10-24",
        "exam_end": "2026-10-25",
        "result_date": "2026-11-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
    {
        "exam_period": "2027年4月",
        "register_start": "2027-01-05",
        "register_end": "2027-01-10",
        "exam_start": "2027-04-10",
        "exam_end": "2027-04-11",
        "result_date": "2027-05-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
    {
        "exam_period": "2027年10月",
        "register_start": "2027-06-10",
        "register_end": "2027-06-15",
        "exam_start": "2027-10-23",
        "exam_end": "2027-10-24",
        "result_date": "2027-11-20",
        "note": "每天上午9:00-11:30，下午14:30-17:00，每半天一科。",
    },
]


def _parse_date(s: str) -> date | None:
    """Try to parse a date string in various Chinese formats."""
    if not s:
        return None
    s = s.strip()
    # Try YYYY-MM-DD
    for fmt in ("%Y-%m-%d", "%Y年%m月%d日", "%Y/%m/%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def crawl_from_website() -> list[dict] | None:
    """Try to crawl exam schedule from zk.hebeea.edu.cn."""
    if not HAS_DEPS:
        print("  requests/bs4 not installed, skip crawl")
        return None

    try:
        print("  Fetching %s ..." % SOURCE_URL)
        resp = requests.get(SOURCE_URL, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding or "utf-8"
        html = resp.text
        print("  Got %d bytes" % len(html))

        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(separator="\n")

        # Look for date patterns like "2026年4月11日" "2026年10月24日"
        # and registration patterns like "报名时间" "考试时间" "成绩"
        schedules = []

        # Find announcement links that mention 报名 or 考试
        links = soup.find_all("a", href=True)
        announcement_urls = []
        for a in links:
            link_text = a.get_text(strip=True)
            if any(kw in link_text for kw in ("报名", "考试安排", "开考", "日程")):
                href = a["href"]
                if not href.startswith("http"):
                    href = SOURCE_URL.rstrip("/") + "/" + href.lstrip("/")
                announcement_urls.append((link_text, href))
                print("  Found link: %s -> %s" % (link_text, href))

        # Try to parse each announcement
        for title, url in announcement_urls[:5]:
            try:
                detail_resp = requests.get(url, headers=HEADERS, timeout=10)
                detail_resp.encoding = detail_resp.apparent_encoding or "utf-8"
                detail_soup = BeautifulSoup(detail_resp.text, "html.parser")
                detail_text = detail_soup.get_text()

                # Extract dates using regex
                date_pattern = re.compile(r"(\d{4})年(\d{1,2})月(\d{1,2})日")
                dates_found = date_pattern.findall(detail_text)

                if dates_found:
                    print("    Found %d dates in: %s" % (len(dates_found), title[:40]))
                    # We found dates but structured extraction is complex
                    # Store raw for manual review

            except Exception as e:
                print("    Failed to fetch %s: %s" % (url[:60], e))

        # If we found structured data, return it
        if schedules:
            return schedules

        print("  Could not extract structured schedule data from website")
        return None

    except Exception as e:
        print("  Crawl failed: %s" % e)
        return None


def upsert_schedules(db, schedules: list[dict], source: str, dry_run: bool) -> int:
    """Insert or update exam schedule records."""
    count = 0
    today = date.today()

    for s in schedules:
        exam_period = s["exam_period"]
        existing = db.query(ExamSchedule).filter(ExamSchedule.exam_period == exam_period).first()

        exam_start = _parse_date(s["exam_start"]) if isinstance(s["exam_start"], str) else s["exam_start"]
        exam_end = _parse_date(s.get("exam_end", "")) if isinstance(s.get("exam_end"), str) else s.get("exam_end")
        register_start = _parse_date(s.get("register_start", "")) if isinstance(s.get("register_start"), str) else s.get("register_start")
        register_end = _parse_date(s.get("register_end", "")) if isinstance(s.get("register_end"), str) else s.get("register_end")
        result_date = _parse_date(s.get("result_date", "")) if isinstance(s.get("result_date"), str) else s.get("result_date")

        is_past = 1 if exam_start and exam_start < today else 0

        if existing:
            print("  UPDATE: %s" % exam_period)
            if not dry_run:
                existing.register_start = register_start
                existing.register_end = register_end
                existing.exam_start = exam_start
                existing.exam_end = exam_end
                existing.result_date = result_date
                existing.note = s.get("note")
                existing.source_url = source
                existing.crawled_at = datetime.utcnow()
                existing.is_past = is_past
        else:
            print("  INSERT: %s" % exam_period)
            if not dry_run:
                db.add(ExamSchedule(
                    exam_period=exam_period,
                    register_start=register_start,
                    register_end=register_end,
                    exam_start=exam_start,
                    exam_end=exam_end,
                    result_date=result_date,
                    note=s.get("note"),
                    source_url=source,
                    crawled_at=datetime.utcnow(),
                    is_past=is_past,
                ))
        count += 1

    return count


def main() -> None:
    parser = argparse.ArgumentParser(description="爬取/更新河北省自考考试日程")
    parser.add_argument("--dry-run", action="store_true", help="只报告不写库")
    parser.add_argument("--fallback-only", action="store_true", help="不爬取，直接用兜底数据")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        print("=== 河北省自考考试日程更新 ===")
        print("来源: %s" % SOURCE_URL)
        print()

        schedules = None
        source = SOURCE_URL

        if not args.fallback_only:
            print("1. 尝试从网站爬取...")
            schedules = crawl_from_website()

        if schedules is None:
            print("2. 使用兜底数据（手工维护）...")
            schedules = FALLBACK_SCHEDULES
            source = "fallback (manual)"

        print("\n3. 写入数据库...")
        count = upsert_schedules(db, schedules, source, args.dry_run)
        print("   合计: %d 条" % count)

        if not args.dry_run:
            db.commit()
            print("\n[OK] 更新完成!")
        else:
            print("\n[dry-run] 未写入数据库")

    except Exception as e:
        db.rollback()
        print("[FAIL] %s" % e)
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
