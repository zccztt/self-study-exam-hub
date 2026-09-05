# -*- coding: utf-8 -*-
"""探测不同查询式（而非域名）对答案召回的影响。

用法:
    python -m scripts.probe_query
"""

from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.services.search_client import search_client

ANSWER_RE = re.compile(r"(?:答案|正确答案|参考答案)\s*[:：】]?\s*[A-D]")
OPTION_RE = re.compile(r"(?:^|\n)\s*[A-F][\.、．\)]")

# 每个查询式针对同一目标，比较答案召回差异
QUERIES = [
    "2024年10月自考00277行政管理学真题及答案解析",
    "自考 行政管理学 真题 【答案】 单项选择题",
    "00277 行政管理学 历年真题 答案 filetype:pdf",
    "自考行政管理学真题答案 site:sohu.com",
]


def main() -> None:
    for query in QUERIES:
        print(f"\n=== {query} ===", flush=True)
        t0 = time.time()
        try:
            results = search_client.unified_search(query, max_results=5)
        except Exception as exc:
            print(f"  搜索失败 {type(exc).__name__}", flush=True)
            continue
        print(f"  搜索 {time.time()-t0:.1f}s 命中 {len(results)} 条", flush=True)

        total_answers = 0
        for result in results[:3]:
            if not result.url:
                continue
            host = urlparse(result.url).netloc
            try:
                text = search_client.extract(result.url)
            except Exception as exc:
                print(f"    抽取失败 {type(exc).__name__} {host}", flush=True)
                continue
            if not text:
                print(f"    空正文 {host}", flush=True)
                continue
            answers = len(ANSWER_RE.findall(text))
            options = len(OPTION_RE.findall(text))
            total_answers += answers
            flag = " <<<" if answers > 0 else ""
            print(
                f"    答案{answers:3d} 选项{options:3d} {len(text):6d}字 {host}{flag}",
                flush=True,
            )
        print(f"  → 该查询式答案总数: {total_answers}", flush=True)


if __name__ == "__main__":
    main()
