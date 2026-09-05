# -*- coding: utf-8 -*-
"""Main crawl runner script.

Usage:
    # Crawl a single province (Hebei)
    python -m scripts.crawl_majors --province 13

    # Crawl multiple provinces
    python -m scripts.crawl_majors --province 13 44 33

    # Crawl all supported provinces
    python -m scripts.crawl_majors --all

    # Dry run (crawl but don't save to DB)
    python -m scripts.crawl_majors --province 13 --dry-run
"""

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models.crawl_log import CrawlLog
from scripts.crawlers import CrawlResult
from scripts.crawlers.zikaosw_crawler import ZikaswCrawler
from scripts.crawlers.data_importer import DataImporter

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def save_crawl_log(db, result: CrawlResult, import_stats: dict) -> None:
    """Save crawl result to CrawlLog table."""
    duration = None
    if result.finished_at and result.started_at:
        duration = int((result.finished_at - result.started_at).total_seconds())

    log = CrawlLog(
        source=result.source,
        province_code=result.province_code,
        status="success" if result.success else "failed",
        schools_found=result.schools_found,
        majors_found=result.majors_found,
        majors_created=import_stats.get("majors_created", 0),
        majors_updated=import_stats.get("majors_updated", 0),
        courses_found=result.courses_found,
        links_created=import_stats.get("links_created", 0),
        error_count=len(result.errors),
        errors=result.errors if result.errors else None,
        duration_seconds=duration,
        started_at=result.started_at,
        finished_at=result.finished_at,
    )
    db.add(log)
    db.commit()


def run_crawl(province_codes: list, dry_run: bool = False, source: str = "zikaosw") -> None:
    """Run the crawl for specified provinces."""
    # Select crawler
    if source == "zikaosw":
        crawler = ZikaswCrawler(min_delay=2.0, max_delay=4.0)
    else:
        logger.error(f"Unknown source: {source}")
        return

    db = SessionLocal() if not dry_run else None

    try:
        for code in province_codes:
            logger.info(f"{'[DRY RUN] ' if dry_run else ''}Starting crawl: province={code} source={source}")

            # Crawl
            result = crawler.crawl_province(code)
            logger.info(result.summary())

            if result.errors:
                for err in result.errors[:5]:
                    logger.warning(f"  Error: {err}")

            if dry_run:
                # Print what would be imported
                logger.info(f"  [DRY RUN] Would import: {result.majors_found} majors, {result.courses_found} courses")
                continue

            if not result.success or result.majors_found == 0:
                logger.warning(f"  Skipping import for province {code}: crawl {'failed' if not result.success else 'found no data'}")
                save_crawl_log(db, result, {})
                continue

            # Import to database
            # Access parsed majors from the crawl result via crawler internals
            # Re-fetch the province page to get parsed data (already cached in browser)
            url = f"{crawler.base_url}/zkzy/province-{code}.html"
            html = crawler.browser.fetch(url, wait_selector="a[href*='major-']")
            if html:
                parsed_majors = crawler._parse_province_page(html)
                # Convert to importer format
                majors_data = []
                for pm in parsed_majors:
                    if pm.courses:  # Only import majors with courses parsed
                        majors_data.append(pm.to_dict())
                    else:
                        # Re-fetch detail if not already done
                        detail_url = f"{crawler.base_url}/zkzy/major-{pm.site_id}.html"
                        detail_html = crawler.browser.fetch(detail_url, wait_selector="table")
                        if detail_html:
                            crawler._parse_major_detail(pm, detail_html)
                        if pm.courses:
                            majors_data.append(pm.to_dict())

                if majors_data:
                    importer = DataImporter(db)
                    import_stats = importer.import_majors(code, majors_data)
                    logger.info(f"  Imported: {import_stats}")
                    save_crawl_log(db, result, import_stats)
                else:
                    logger.warning(f"  No importable data for province {code}")
                    save_crawl_log(db, result, {})
            else:
                save_crawl_log(db, result, {})

    finally:
        crawler.close()
        if db:
            db.close()


def main():
    parser = argparse.ArgumentParser(description="Crawl self-study exam major/course data")
    parser.add_argument("--province", nargs="+", help="Province codes to crawl (e.g., 13 44 33)")
    parser.add_argument("--all", action="store_true", help="Crawl all supported provinces")
    parser.add_argument("--dry-run", action="store_true", help="Crawl but don't save to database")
    parser.add_argument("--source", default="zikaosw", choices=["zikaosw"], help="Data source to crawl")
    args = parser.parse_args()

    if args.all:
        crawler = ZikaswCrawler()
        province_codes = crawler.supported_provinces()
    elif args.province:
        province_codes = args.province
    else:
        # Default: just Hebei
        province_codes = ["13"]

    logger.info(f"Crawling {len(province_codes)} province(s): {', '.join(province_codes)}")
    run_crawl(province_codes, dry_run=args.dry_run, source=args.source)


if __name__ == "__main__":
    main()
