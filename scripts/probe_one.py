# -*- coding: utf-8 -*-
"""快速探测单个渠道，带耗时统计和结果落盘。

用法:
    python -m scripts.probe_one zikao365.com 自考365
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.search_client import search_client

ANSWER_RE = re.compile(r"(?:答案|正确答案|参考答案)\s*[:：】]?\s*[A-D]")
OPTION_RE = re.compile(r"(?:^|\n)\s*[A-F][\.、．\)]")
STEM_RE = re.compile(r"(?:^|\n)\s*\d{1,2}[\.、．]")

OUT_PATH = Path("data/channel_probe.jsonl")


def main() -> None:
    domain = sys.argv[1] if len(sys.argv) > 1 else ""
    label = sys.argv[2] if len(sys.argv) > 2 else (domain or "全网")

    base = "2024年10月自考 00277 行政管理学 真题 答案"
    query = f"site:{domain} {base}" if domain else base

    t0 = time.time()
    try:
        results = search_client.unified_search(query, max_results=4)
    except Exception as exc:
        print(f"{label}\tSEARCH_FAIL\t{type(exc).__name__}", flush=True)
        return
    t_search = time.time() - t0

    if domain:
        results = [r for r in results if domain in (urlparse(r.url or "").netloc or "")]

    print(f"{label}: 搜索{t_search:.1f}s 命中{len(results)}条", flush=True)
    if not results:
        _write({"label": label, "domain": domain, "hits": 0, "best_answers": 0})
        print(f"{label}\tNO_HIT", flush=True)
        return

    best = {"answers": 0, "url": "", "options": 0, "stems": 0, "chars": 0}
    for result in results[:2]:
        t1 = time.time()
        try:
            text = search_client.extract(result.url)
        except Exception as exc:
            print(f"  抽取失败 {type(exc).__name__} {result.url[:60]}", flush=True)
            continue
        elapsed = time.time() - t1
        if not text:
            print(f"  空正文 ({elapsed:.1f}s) {result.url[:60]}", flush=True)
            continue
        stats = {
            "answers": len(ANSWER_RE.findall(text)),
            "options": len(OPTION_RE.findall(text)),
            "stems": len(STEM_RE.findall(text)),
            "chars": len(text),
            "url": result.url,
        }
        print(
            f"  {elapsed:.1f}s 答案{stats['answers']} 选项{stats['options']} "
            f"题号{stats['stems']} {stats['chars']}字 {result.url[:58]}",
            flush=True,
        )
        if stats["answers"] > best["answers"]:
            best = stats

    _write({
        "label": label,
        "domain": domain,
        "hits": len(results),
        "best_answers": best["answers"],
        "best_options": best["options"],
        "best_url": best["url"],
    })
    verdict = "USABLE" if best["answers"] > 0 else "NO_ANSWER"
    print(f"{label}\t{verdict}\t答案{best['answers']}", flush=True)


def _write(record: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
