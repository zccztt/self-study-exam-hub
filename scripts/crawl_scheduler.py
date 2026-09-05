# -*- coding: utf-8 -*-
"""Crawl scheduler: runs periodic data updates.

Usage:
    # Run once immediately
    python -m scripts.crawl_scheduler --once

    # Run as daemon with schedule
    python -m scripts.crawl_scheduler --daemon

Schedule (configurable):
- Monthly 1st: All provinces - major directory update
- Quarterly: Course plan refresh
- Manual trigger via CLI

Requires: pip install apscheduler (optional, for daemon mode)
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.crawl_log import CrawlLog
from scripts.crawlers.zikaosw_crawler import ZikaswCrawler
from scripts.crawlers.data_importer import DataImporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Priority provinces (crawled more frequently)
PRIORITY_PROVINCES = ["13", "44", "33", "32", "42", "43", "51"]

# All provinces
ALL_PROVINCES = ZikaswCrawler.ALL_PROVINCES


def crawl_and_import(province_codes: list, source: str = "zikaosw") -> dict:
    """Crawl provinces and import data. Returns summary stats."""
    crawler = ZikaswCrawler(min_delay=2.5, max_delay=5.0)
    db = SessionLocal()
    total_stats = {"provinces": 0, "majors_found": 0, "majors_created": 0, "links_created": 0, "errors": 0}

    try:
        for code in province_codes:
            logger.info(f"--- Crawling province {code} ---")
            result = crawler.crawl_province(code)
            logger.info(result.summary())

            import_stats = {}
            if result.success and result.majors_found > 0:
                # Import crawled data to database
                # Note: direct import requires re-crawling to get parsed major objects
                # For now, logging only - use crawl_majors.py for full import pipeline
                pass

            # Save crawl log
            duration = None
            if result.finished_at and result.started_at:
                duration = int((result.finished_at - result.started_at).total_seconds())

            log_entry = CrawlLog(
                source=source,
                province_code=code,
                status="success" if result.success else "failed",
                schools_found=result.schools_found,
                majors_found=result.majors_found,
                majors_created=import_stats.get("majors_created", 0),
                majors_updated=import_stats.get("majors_updated", 0),
                courses_found=result.courses_found,
                links_created=import_stats.get("links_created", 0),
                error_count=len(result.errors),
                errors=result.errors[:20] if result.errors else None,
                duration_seconds=duration,
                started_at=result.started_at,
                finished_at=result.finished_at,
            )
            db.add(log_entry)
            db.commit()

            total_stats["provinces"] += 1
            total_stats["majors_found"] += result.majors_found
            total_stats["majors_created"] += import_stats.get("majors_created", 0)
            total_stats["links_created"] += import_stats.get("links_created", 0)
            total_stats["errors"] += len(result.errors)

    finally:
        crawler.close()
        db.close()

    return total_stats


def monthly_full_crawl():
    """Monthly full crawl of all provinces."""
    logger.info("=== Monthly Full Crawl ===")
    stats = crawl_and_import(ALL_PROVINCES)
    logger.info(f"Monthly crawl complete: {stats}")


def weekly_priority_crawl():
    """Weekly crawl of priority provinces."""
    logger.info("=== Weekly Priority Crawl ===")
    stats = crawl_and_import(PRIORITY_PROVINCES)
    logger.info(f"Priority crawl complete: {stats}")


def run_daemon():
    """Run as scheduled daemon using APScheduler."""
    try:
        from apscheduler.schedulers.blocking import BlockingScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.error("APScheduler not installed. Run: pip install apscheduler")
        logger.error("Falling back to single run.")
        weekly_priority_crawl()
        return

    scheduler = BlockingScheduler()

    # Monthly 1st at 03:00 - full crawl
    scheduler.add_job(
        monthly_full_crawl,
        CronTrigger(day=1, hour=3, minute=0),
        id="monthly_full_crawl",
        name="Monthly full province crawl",
    )

    # Every Monday at 04:00 - priority provinces
    scheduler.add_job(
        weekly_priority_crawl,
        CronTrigger(day_of_week="mon", hour=4, minute=0),
        id="weekly_priority_crawl",
        name="Weekly priority province crawl",
    )

    logger.info("Scheduler started. Press Ctrl+C to exit.")
    logger.info("Jobs:")
    for job in scheduler.get_jobs():
        logger.info(f"  {job.name}: {job.trigger}")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped.")


def main():
    parser = argparse.ArgumentParser(description="Self-study exam data crawl scheduler")
    parser.add_argument("--once", action="store_true", help="Run once and exit (priority provinces)")
    parser.add_argument("--full", action="store_true", help="Run full crawl of all provinces and exit")
    parser.add_argument("--daemon", action="store_true", help="Run as scheduled daemon")
    parser.add_argument("--province", nargs="+", help="Specific provinces to crawl")
    args = parser.parse_args()

    if args.daemon:
        run_daemon()
    elif args.full:
        monthly_full_crawl()
    elif args.province:
        stats = crawl_and_import(args.province)
        logger.info(f"Custom crawl complete: {stats}")
    else:
        weekly_priority_crawl()


if __name__ == "__main__":
    main()
