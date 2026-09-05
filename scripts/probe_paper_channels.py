# -*- coding: utf-8 -*-
"""探测各真题渠道的可用性：能否搜到、能否抽取正文、正文是否含答案。

只读脚本，不写数据库。用于在建采集管线前确认渠道的真实产出能力。

用法:
    python -m scripts.probe_paper_channels
    python -m scripts.probe_paper_channels --only zikao365,sohu
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.search_client import search_client

# (渠道名, 域名)。域名为空表示不限站点的全网搜索。
CHANNELS: list[tuple[str, str]] = [
    ("自考365", "zikao365.com"),
    ("自考生网", "zikaosw.cn"),
    ("环球网校", "hqwx.com"),
    ("华夏大地教育网", "edu-edu.com"),
    ("自考真题下载站", "zikaoda.com"),
    ("百分自考网", "exam100.net"),
    ("咱考网", "zankao.cn"),
    ("51自考", "51zikao.net"),
    ("搜狐", "sohu.com"),
    ("百家号", "baijiahao.baidu.com"),
    ("知乎", "zhihu.com"),
    ("GitHub", "github.com"),
    ("豆丁文库", "docin.com"),
    ("道客巴巴", "doc88.com"),
    ("河北考试院", "hebeea.edu.cn"),
    ("全网搜索", ""),
]

# 正文特征
ANSWER_RE = re.compile(r"(?:答案|正确答案|参考答案)\s*[:：】]?\s*[A-D]")
OPTION_RE = re.compile(r"(?:^|\n)\s*[A-F][\.、．\)]")
STEM_RE = re.compile(r"(?:^|\n)\s*\d{1,2}[\.、．]")

PROBE_TARGETS = [("00277", "行政管理学", 2024, 10), ("00230", "合同法", 2024, 10)]


def build_query(domain: str, code: str, name: str, year: int, month: int) -> str:
    base = f"{year}年{month}月自考 {code} {name} 真题 答案"
    return f"site:{domain} {base}" if domain else base


def score_text(text: str) -> dict:
    """统计正文中的试题特征数量。"""
    return {
        "chars": len(text),
        "answers": len(ANSWER_RE.findall(text)),
        "options": len(OPTION_RE.findall(text)),
        "stems": len(STEM_RE.findall(text)),
    }


def probe_channel(label: str, domain: str, max_extract: int = 2) -> dict:
    """返回该渠道的探测结果汇总。"""
    hits, extracted, with_answers = 0, 0, 0
    best: dict | None = None
    errors: list[str] = []

    for code, name, year, month in PROBE_TARGETS:
        query = build_query(domain, code, name, year, month)
        try:
            results = search_client.unified_search(query, max_results=4)
        except Exception as exc:
            errors.append(f"搜索失败 {type(exc).__name__}")
            continue

        # 限定在目标域名内（全网搜索时不过滤）
        if domain:
            results = [r for r in results if domain in (urlparse(r.url or "").netloc or "")]
        hits += len(results)

        for result in results[:max_extract]:
            if not result.url:
                continue
            try:
                text = search_client.extract(result.url)
            except Exception as exc:
                errors.append(f"抽取失败 {type(exc).__name__}")
                continue
            if not text or len(text) < 300:
                continue
            extracted += 1
            stats = score_text(text)
            if stats["answers"] > 0:
                with_answers += 1
            if best is None or stats["answers"] > best["stats"]["answers"]:
                best = {"url": result.url, "stats": stats}

    return {
        "label": label,
        "domain": domain or "(全网)",
        "hits": hits,
        "extracted": extracted,
        "with_answers": with_answers,
        "best": best,
        "errors": errors[:2],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="探测真题渠道可用性")
    parser.add_argument("--only", help="只测指定渠道，逗号分隔域名关键词")
    args = parser.parse_args()

    channels = CHANNELS
    if args.only:
        keys = [k.strip() for k in args.only.split(",") if k.strip()]
        channels = [c for c in CHANNELS if any(k in c[1] or k in c[0] for k in keys)]

    print(f"搜索源: {search_client.available_sources}")
    print(f"探测 {len(channels)} 个渠道，每渠道 {len(PROBE_TARGETS)} 个目标\n")
    print(f"{'渠道':16s} {'搜到':>4s} {'抽取':>4s} {'含答案':>5s}  最佳页面特征")
    print("-" * 78)

    usable, unusable = [], []
    for label, domain in channels:
        r = probe_channel(label, domain)
        mark = "OK " if r["with_answers"] > 0 else "-- "
        detail = ""
        if r["best"]:
            s = r["best"]["stats"]
            detail = f"答案{s['answers']} 选项{s['options']} 题号{s['stems']} {s['chars']}字"
        elif r["errors"]:
            detail = r["errors"][0]
        print(f"{mark}{label:14s} {r['hits']:>4d} {r['extracted']:>4d} {r['with_answers']:>5d}  {detail}")
        (usable if r["with_answers"] > 0 else unusable).append(r)

    print("-" * 78)
    print(f"\n可用渠道 ({len(usable)}):")
    for r in usable:
        s = r["best"]["stats"]
        print(f"  {r['label']} — 答案标记{s['answers']}个")
        print(f"    {r['best']['url'][:88]}")
    print(f"\n未产出答案的渠道 ({len(unusable)}): {', '.join(r['label'] for r in unusable)}")


if __name__ == "__main__":
    main()

