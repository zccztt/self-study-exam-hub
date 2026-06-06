#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fetch Bilibili video metadata and export it for data_import.py.

The crawler only reads public metadata endpoints and writes normalized JSON.
Use a conservative delay for keyword searches and respect target-site rules.
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import httpx


SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
VIEW_URL = "https://api.bilibili.com/x/web-interface/view"
DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    ),
    "Referer": "https://www.bilibili.com/",
}


def extract_bvid(value: str) -> Optional[str]:
    match = re.search(r"(BV[0-9A-Za-z]{10})", value)
    return match.group(1) if match else None


def clean_html(value: Any) -> str:
    return re.sub(r"<[^>]+>", "", str(value or "")).strip()


def parse_publish_date(timestamp: Any) -> Optional[str]:
    if isinstance(timestamp, str) and not timestamp.isdigit():
        for fmt in ("%Y-%m-%d", "%Y/%m/%d"):
            try:
                return datetime.strptime(timestamp, fmt).replace(tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except (TypeError, ValueError, OSError):
        return None


def parse_count(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, int):
        return value
    text = str(value).replace(",", "").strip()
    if not text or text == "--":
        return 0
    multiplier = 1
    if text.endswith("万"):
        multiplier = 10000
        text = text[:-1]
    elif text.endswith("亿"):
        multiplier = 100000000
        text = text[:-1]
    try:
        return int(float(text) * multiplier)
    except ValueError:
        return 0


def parse_duration(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value)
    if text.isdigit():
        return int(text)
    parts = [int(part) for part in text.split(":") if part.isdigit()]
    if len(parts) == 3:
        return parts[0] * 3600 + parts[1] * 60 + parts[2]
    if len(parts) == 2:
        return parts[0] * 60 + parts[1]
    return None


def normalize_video(
    item: Dict[str, Any],
    subject_id: Optional[int],
    subject_name: Optional[str],
    chapter_id: Optional[int],
    chapter_name: Optional[str],
    knowledge_points: List[str],
    tags: List[str],
) -> Dict[str, Any]:
    bvid = item.get("bvid") or extract_bvid(str(item.get("arcurl") or item.get("url") or ""))
    url = item.get("arcurl") or item.get("short_link_v2") or (f"https://www.bilibili.com/video/{bvid}" if bvid else "")
    stat = item.get("stat") or {}
    owner = item.get("owner") or {}
    tag_names = [clean_html(item.get("typename"))] if item.get("typename") else []
    tag_names.extend(tags)

    return {
        "title": clean_html(item.get("title")),
        "url": url,
        "source": "bilibili",
        "duration": parse_duration(item.get("duration")),
        "author": clean_html(item.get("author") or owner.get("name") or item.get("mid")),
        "view_count": parse_count(stat.get("view") or item.get("play")),
        "publish_date": parse_publish_date(item.get("pubdate") or item.get("senddate")),
        "subject_id": subject_id,
        "subject_name": subject_name,
        "chapter_id": chapter_id,
        "chapter_name": chapter_name,
        "thumbnail": item.get("pic"),
        "description": clean_html(item.get("description") or item.get("desc")),
        "knowledge_points": knowledge_points,
        "tags": [tag for tag in dict.fromkeys(tag_names) if tag],
    }


class BilibiliCrawler:
    def __init__(self, timeout: float = 15.0) -> None:
        self.client = httpx.Client(headers=DEFAULT_HEADERS, timeout=timeout, follow_redirects=True)

    def close(self) -> None:
        self.client.close()

    def search(self, keyword: str, pages: int, page_size: int, delay: float) -> List[Dict[str, Any]]:
        videos: List[Dict[str, Any]] = []
        for page in range(1, pages + 1):
            params = {
                "search_type": "video",
                "keyword": keyword,
                "page": page,
                "page_size": page_size,
            }
            response = self.client.get(SEARCH_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            if payload.get("code") != 0:
                raise RuntimeError(f"Bilibili search failed: {payload.get('message')}")
            videos.extend(payload.get("data", {}).get("result") or [])
            if page < pages:
                time.sleep(delay)
        return videos

    def view(self, bvid: str) -> Dict[str, Any]:
        response = self.client.get(VIEW_URL, params={"bvid": bvid})
        response.raise_for_status()
        payload = response.json()
        if payload.get("code") != 0:
            raise RuntimeError(f"Bilibili view failed for {bvid}: {payload.get('message')}")
        return payload.get("data") or {}


def load_bvids(values: Iterable[str], file_path: Optional[Path]) -> List[str]:
    candidates = list(values)
    if file_path:
        candidates.extend(file_path.read_text(encoding="utf-8-sig").splitlines())
    bvids = []
    for value in candidates:
        bvid = extract_bvid(value.strip())
        if bvid:
            bvids.append(bvid)
    return list(dict.fromkeys(bvids))


def write_json(path: Path, records: List[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Bilibili video metadata.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--keyword", help="Search keyword.")
    source.add_argument("--bvid", action="append", default=[], help="BV id or video URL. Can be repeated.")
    source.add_argument("--bvid-file", type=Path, help="Text file containing BV ids or URLs, one per line.")
    parser.add_argument("--pages", type=int, default=1, help="Search pages to fetch.")
    parser.add_argument("--page-size", type=int, default=20, help="Search page size.")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between search pages in seconds.")
    parser.add_argument("--subject-id", type=int)
    parser.add_argument("--subject-name")
    parser.add_argument("--chapter-id", type=int)
    parser.add_argument("--chapter-name")
    parser.add_argument("--knowledge-point", action="append", default=[])
    parser.add_argument("--tag", action="append", default=[])
    parser.add_argument("--output", type=Path, default=Path("data/videos/bilibili_videos.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    crawler = BilibiliCrawler()
    try:
        raw_items = []
        if args.keyword:
            raw_items = crawler.search(args.keyword, args.pages, args.page_size, args.delay)
        else:
            for bvid in load_bvids(args.bvid, args.bvid_file):
                raw_items.append(crawler.view(bvid))

        records = [
            normalize_video(
                item,
                args.subject_id,
                args.subject_name,
                args.chapter_id,
                args.chapter_name,
                args.knowledge_point,
                args.tag,
            )
            for item in raw_items
            if clean_html(item.get("title"))
        ]
        write_json(args.output, records)
        print(f"Exported {len(records)} videos to {args.output}")
        return 0
    finally:
        crawler.close()


if __name__ == "__main__":
    sys.exit(main())
