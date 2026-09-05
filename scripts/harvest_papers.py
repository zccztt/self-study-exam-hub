# -*- coding: utf-8 -*-
"""多渠道真题采集管线。

流程: 多渠道搜索 -> 全部落 past_paper_sources 审计 -> 抽取正文(HTML/PDF/图片)
      -> 校验是否真题 -> 解析入题库 -> 标记答案来源

设计要点:
  * 视频类只存链接, 不尝试解析(按需求)
  * 每个 URL 先入 past_paper_sources, 解析失败也留痕便于回溯和重试
  * 入题库前做真题校验, 拒绝招生简章/目录页/商品页
  * 题目按 content 去重, 已存在则复用不重复插入
  * 有答案的标 crawled, 无答案的标 pending(后续可补)

用法:
    python -m scripts.harvest_papers --subject 00277 --year 2024 --month 10
    python -m scripts.harvest_papers --all --periods 2024-10,2023-10
    python -m scripts.harvest_papers --all --limit-subjects 5 --dry-run
"""

from __future__ import annotations

import argparse
import io
import random
import re
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from backend.database import SessionLocal
from backend.models import Chapter, PastPaper, PastPaperSource, Question, Subject
from backend.models.question import AnswerSource, PENDING_ANSWER_MARKER
from backend.services.search_client import SearchResult, search_client
from scripts.parse_paper import parse_paper_text

# --------------------------------------------------------------------------
# 渠道与查询式
# --------------------------------------------------------------------------

# 实测产出答案的渠道优先。空域名表示全网搜索。
# 探测结果(scripts/probe_one.py): 仅 sohu.com 稳定产出答案标记,
# 其余站点多返回招生简章/专业目录, 保留是为了捞题干(答案后补)。
CHANNELS: list[tuple[str, str]] = [
    ("搜狐", "sohu.com"),
    ("全网", ""),
    ("自考365", "zikao365.com"),
    ("自考生网", "zikaosw.cn"),
    ("百分自考", "exam100.net"),
    ("华夏大地", "edu-edu.com"),
    ("环球网校", "hqwx.com"),
    ("知乎", "zhihu.com"),
    ("百家号", "baijiahao.baidu.com"),
    ("咱考网", "zankao.cn"),
    ("自考真题站", "zikaoda.com"),
]

# 批量跑时只用实测有产出的渠道, 省掉大量空转。
# 探测显示除 sohu 外其余站点基本不返回真题正文。
FAST_CHANNELS: list[tuple[str, str]] = [
    ("搜狐", "sohu.com"),
    ("全网", ""),
]

VIDEO_HOSTS = ("bilibili.com", "youtube.com", "youtu.be", "v.qq.com", "douyin.com", "ixigua.com")
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp")
PDF_EXTENSIONS = (".pdf",)
DOC_EXTENSIONS = (".doc", ".docx")

# 请求间隔, 避免把搜索服务打挂
DELAY_RANGE = (0.6, 1.6)

# 全国卷特征词 —— 用于优先排序
NATIONAL_MARKERS = ("全国", "统考", "全国统一")
# 省级命题特征词 —— 命中则降权
PROVINCE_MARKERS = (
    "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江", "上海",
    "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南", "湖北", "湖南",
    "广东", "广西", "海南", "重庆", "四川", "贵州", "云南", "西藏", "陕西",
    "甘肃", "青海", "宁夏", "新疆",
)


def build_queries(
    code: str, name: str, year: int, month: int, *, channels: list[tuple[str, str]] | None = None
) -> list[tuple[str, str]]:
    """为一个 (科目, 期次) 生成 (渠道名, 查询式) 列表。

    全国卷优先: 第一条查询显式带"全国", 后续再放宽。
    """
    used = channels if channels is not None else CHANNELS
    base = f"{year}年{month}月自考 {code} {name} 真题"
    queries: list[tuple[str, str]] = []
    for label, domain in used:
        prefix = f"site:{domain} " if domain else ""
        # 全国卷优先: 同渠道先搜全国卷, 再搜不限定的
        queries.append((f"{label}-全国", f"{prefix}全国{base} 试题"))
        queries.append((label, f"{prefix}{base} 答案"))
    queries.append(("全网-真题变体", f"全国{base} 试题 单项选择题"))
    return queries


def national_rank(result: SearchResult) -> int:
    """全国卷排序权重, 越小越优先。

    0 = 明确全国卷, 1 = 未标注, 2 = 明确省级命题
    """
    text = f"{result.title or ''} {result.content or ''}"[:600]
    if any(token in text for token in NATIONAL_MARKERS):
        return 0
    if any(token in text for token in PROVINCE_MARKERS):
        return 2
    return 1


# --------------------------------------------------------------------------
# 媒体类型判定与正文抽取
# --------------------------------------------------------------------------

def media_type(result: SearchResult) -> str:
    url = (result.url or "").lower().split("?", 1)[0]
    host = urlparse(url).netloc
    title = (result.title or "").lower()
    if any(token in host for token in VIDEO_HOSTS):
        return "video"
    if url.endswith(PDF_EXTENSIONS) or ".pdf" in title:
        return "pdf"
    if url.endswith(DOC_EXTENSIONS):
        return "doc"
    if url.endswith(IMAGE_EXTENSIONS):
        return "image"
    return "html"


def canonical_url(url: str) -> str:
    """归一化 URL, 让同一篇文章的 PC/移动/带参版本合并为一条。"""
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("m."):
        host = host[2:]
    if host.startswith("www."):
        host = host[4:]
    # 丢弃追踪参数, 只保留路径
    return f"{host}{parsed.path.rstrip('/')}"


def download_bytes(url: str, timeout: int = 40) -> tuple[bytes | None, str | None]:
    """下载文件原文。"""
    try:
        import httpx

        response = httpx.get(
            url,
            follow_redirects=True,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
        )
        response.raise_for_status()
        return response.content, None
    except Exception as exc:
        return None, f"下载失败: {type(exc).__name__}"


def extract_doc(url: str) -> tuple[str | None, str | None, bytes | None]:
    """下载 doc/docx 并抽取文字。返回 (文本, 错误, 原文字节)。"""
    data, error = download_bytes(url)
    if not data:
        return None, error, None
    # docx 是 zip, 复用 parse_paper 的 docx 解析
    try:
        import zipfile
        from xml.etree import ElementTree

        with zipfile.ZipFile(io.BytesIO(data)) as archive:
            xml_content = archive.read("word/document.xml")
        root = ElementTree.fromstring(xml_content)
        namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
        paragraphs = []
        for paragraph in root.findall(".//w:p", namespace):
            texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
            if texts:
                paragraphs.append("".join(texts))
        text = "\n".join(paragraphs)
        if text.strip():
            return text, None, data
        return None, "DOCX 无文字内容", data
    except Exception as exc:
        # 老式 .doc 二进制格式无法用 zip 解析
        return None, f"DOC 解析失败({type(exc).__name__}), 已保留原文", data


def extract_pdf(url: str) -> tuple[str | None, str | None]:
    try:
        import httpx
        from pypdf import PdfReader

        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(response.content)
            path = Path(handle.name)
        try:
            text = "\n".join(page.extract_text() or "" for page in PdfReader(str(path)).pages)
        finally:
            path.unlink(missing_ok=True)
        if text.strip():
            return text, None
        return None, "PDF 无文本层, 需 OCR"
    except Exception as exc:
        return None, f"PDF 解析失败: {type(exc).__name__}"


def extract_image(url: str) -> tuple[str | None, str | None]:
    try:
        import httpx
        import pytesseract
        from PIL import Image

        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
        text = pytesseract.image_to_string(
            Image.open(io.BytesIO(response.content)), lang="chi_sim+eng"
        )
        if text.strip():
            return text, None
        return None, "图片 OCR 未识别到文字"
    except ImportError:
        return None, "OCR 依赖未安装(需 tesseract), 保留链接"
    except Exception as exc:
        return None, f"图片 OCR 失败: {type(exc).__name__}"


def extract_content(result: SearchResult, kind: str) -> tuple[str | None, str | None]:
    """按媒体类型抽取正文。视频只留链接。"""
    if kind == "video":
        return None, "视频来源仅保存链接"
    if kind == "pdf":
        return extract_pdf(result.url)
    if kind == "doc":
        text, error, raw = extract_doc(result.url)
        if raw:
            _store_file_to_minio(result.url, raw)
        return text, error
    if kind == "image":
        return extract_image(result.url)
    try:
        text = search_client.extract(result.url)
    except Exception as exc:
        return None, f"正文抽取失败: {type(exc).__name__}"
    if text and len(text.strip()) >= 200:
        return text, None
    return None, "正文过短或抽取为空, 保留链接待人工处理"


def _store_file_to_minio(url: str, data: bytes) -> None:
    """尝试把下载的文件存到 MinIO, 失败不阻断主流程。"""
    try:
        from backend.minio_client import minio_client

        if not minio_client.is_available:
            return
        import hashlib
        import mimetypes

        ext = Path(urlparse(url).path).suffix.lower() or ".bin"
        name = Path(urlparse(url).path).name or "file"
        file_hash = hashlib.sha256(data).hexdigest()[:12]
        obj = f"papers/{file_hash}_{name}"
        ct = mimetypes.guess_type(name)[0] or "application/octet-stream"
        minio_client.upload_file(obj, data, ct)
    except Exception:
        pass  # MinIO 不可用时静默跳过


# --------------------------------------------------------------------------
# 真题校验 —— 拒绝招生简章/专业目录/商品页
# --------------------------------------------------------------------------

EXAM_MARKERS = ("试题", "单项选择题", "多项选择题", "课程代码", "考试结束", "本试卷")
JUNK_MARKERS = ("招生简章", "报名时间", "专业目录", "立即购买", "优惠券", "加入购物车", "学费")
# 选项标记: 兼容行首式(A.\n B.\n) 与同行式(A.xx B.xx C.xx)
OPTION_LINE_RE = re.compile(
    r"(?:(?:^|\n)\s*|\s{2,}|(?<=[一-龥\)）。；;]))([A-F])[\.、．\)]"
)
ANSWER_LINE_RE = re.compile(r"(?:答案|正确答案|参考答案)\s*[:：】]?\s*[A-D]")

# --- 题干清洗 ---
# 解析器会把试卷分节标题和推广话术并入题干, 这里逐行剔除。
SECTION_HEADER_RE = re.compile(
    r"^\**\s*(?:第[一二三四五六七八九十]+部分|[一二三四五六七八九十]+\s*[、.]\s*"
    r"(?:单项|多项)?选择题|[一二三四五六七八九十]+\s*[、.]\s*(?:简答|论述|案例分析|名词解释|填空)题)"
)
PROMO_RE = re.compile(
    r"(?:绿泡泡|微信|公众号|加\s*群|扫码|关注|获取(?:完整|全套)|资料领取|"
    r"客服|QQ\s*[:：]?\s*\d|shilaoshi|本大题共)"
)
# 多选题的题干特征: "哪些"/"...的有"/"正确的有" 等
MULTI_HINT_RE = re.compile(r"(?:哪些|下列选项中.{0,12}(?:的有|正确的有|错误的有)|的有$|正确的有$|错误的有$)")


# 同行选项拆行: "A.甲 B.乙 C.丙 D.丁" -> 每个选项独立成行
INLINE_OPTION_SPLIT_RE = re.compile(r"(?<!^)(?<![A-Za-z0-9])([A-F][\.、．\)])\s*")
# 题号拆行: "...。2.下一题" -> 题号前换行
INLINE_QUESTION_SPLIT_RE = re.compile(r"(?<=[。？！\)）])\s*(\d{1,2}[\.、．])\s*(?=[^\d])")
# 选项标记统一判定: 用于 normalize_layout 判断是否需要拆行
OPTION_MARKER_SIMPLE = re.compile(r"[A-F][\.、．\)]")


def normalize_layout(text: str) -> str:
    """把同行排列的选项/题号拆成独立行, 供行式解析器识别。"""
    lines = []
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        # 该行含 2 个以上选项标记时才拆, 避免误伤正常句子
        if len(OPTION_MARKER_SIMPLE.findall(line)) >= 2:
            line = INLINE_OPTION_SPLIT_RE.sub(r"\n\1", line)
        line = INLINE_QUESTION_SPLIT_RE.sub(r"\n\1", line)
        lines.extend(part.rstrip() for part in line.split("\n") if part.strip())
    return "\n".join(lines)


def clean_stem(content: str) -> str:
    """剔除混入题干的分节标题与推广话术。"""
    kept = []
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if SECTION_HEADER_RE.match(stripped):
            continue
        if PROMO_RE.search(stripped):
            continue
        # 纯 markdown 装饰行
        if re.fullmatch(r"[\*_\-=#\s]+", stripped):
            continue
        kept.append(stripped)
    return "\n".join(kept).strip()


def correct_question_type(question_type: str, options: list, content: str, answer: str) -> str:
    """修正题型。

    parse_paper.infer_question_type 按答案字母数判定, 答案缺失时一律落到
    single_choice。对无答案的题, 改用选项数与题干措辞推断多选。
    """
    letters = re.sub(r"[^A-F]", "", (answer or "").upper())
    if len(letters) > 1:
        return "multiple_choice"
    if letters:
        return question_type
    # 无答案: 5 个以上选项, 或题干含多选措辞 -> 多选
    if options and (len(options) >= 5 or MULTI_HINT_RE.search(content)):
        return "multiple_choice"
    return question_type


@dataclass
class ValidationResult:
    ok: bool
    reason: str = ""
    exam_markers: int = 0
    option_count: int = 0
    answer_count: int = 0


def validate_paper_text(text: str) -> ValidationResult:
    """判断正文是否像一份真题卷。先归一化选项布局再统计。"""
    normalized = normalize_layout(text)
    exam_hits = sum(1 for token in EXAM_MARKERS if token in normalized)
    junk_hits = sum(1 for token in JUNK_MARKERS if token in normalized)
    # 归一化后选项已拆行, 行首匹配需要 MULTILINE
    options = len(re.findall(r"^\s*[A-F][\.、．\)]", normalized, re.MULTILINE))
    answers = len(ANSWER_LINE_RE.findall(normalized))

    if options < 4:
        return ValidationResult(False, f"选项标记仅 {options} 个", exam_hits, options, answers)
    if exam_hits < 1:
        return ValidationResult(False, "缺少试题特征词", exam_hits, options, answers)
    # 垃圾特征多于试题特征时判为非真题页
    if junk_hits > exam_hits:
        return ValidationResult(
            False, f"疑似招生/商品页(junk={junk_hits} > exam={exam_hits})", exam_hits, options, answers
        )
    return ValidationResult(True, "", exam_hits, options, answers)


# --------------------------------------------------------------------------
# 入库
# --------------------------------------------------------------------------

@dataclass
class HarvestStats:
    searched: int = 0
    sources_new: int = 0
    extracted: int = 0
    validated: int = 0
    questions_new: int = 0
    questions_dup: int = 0
    answers_filled: int = 0
    papers_new: int = 0
    notes: list[str] = field(default_factory=list)


def save_source_record(
    db, result: SearchResult, subject: Subject, year: int, month: int, query: str, channel: str
) -> tuple[PastPaperSource, bool]:
    """URL 先落审计表。返回 (记录, 是否新建)。"""
    existing = db.query(PastPaperSource).filter(PastPaperSource.url == result.url).first()
    if existing:
        return existing, False

    kind = media_type(result)
    record = PastPaperSource(
        subject_id=subject.id,
        year=year,
        month=month,
        title=(result.title or result.url)[:300],
        url=result.url,
        source=f"{channel}/{result.source or 'search'}"[:100],
        media_type=kind,
        status="link_only" if kind == "video" else "pending",
        error_message="视频来源仅保存链接" if kind == "video" else None,
        metadata_json={"query": query, "channel": channel, "snippet": (result.content or "")[:1500]},
    )
    db.add(record)
    db.flush()
    return record, True


def import_parsed_questions(
    db, record: PastPaperSource, subject: Subject, stats: HarvestStats
) -> int:
    """把已抽取的正文解析成题目写入题库, 并组卷。"""
    if not record.content_text or not record.year:
        return 0

    parsed = parse_paper_text(
        normalize_layout(record.content_text),
        subject_code=subject.code,
        subject_name=subject.name,
        year=record.year,
        month=record.month,
        source=f"真实真题-采集-{record.url[:60]}",
        default_difficulty="medium",
    )
    if len(parsed) < 5:
        record.status = "link_only"
        record.error_message = f"仅解析出 {len(parsed)} 题, 未达 5 题阈值"
        return 0

    chapters = (
        db.query(Chapter).filter(Chapter.subject_id == subject.id).order_by(Chapter.order).all()
    )
    source_label = f"真实真题-采集-{record.url[:60]}"
    question_ids: list[int] = []

    for index, item in enumerate(parsed):
        content = clean_stem(item.get("content") or "")
        if len(content) < 8:
            continue
        raw_answer = (item.get("answer") or "").strip()
        has_answer = bool(re.fullmatch(r"[A-F]{1,4}", raw_answer.upper()))
        options = item.get("options") or []
        question_type = correct_question_type(
            item["question_type"], options, content, raw_answer
        )

        existing = (
            db.query(Question)
            .filter(Question.subject_id == subject.id, Question.content == content)
            .first()
        )
        if existing:
            question_ids.append(existing.id)
            stats.questions_dup += 1
            # 已有题目缺答案而本次抓到了真实答案 -> 回填
            if has_answer and existing.answer == PENDING_ANSWER_MARKER:
                existing.answer = raw_answer.upper()
                existing.answer_source = AnswerSource.CRAWLED.value
                existing.explanation = item.get("explanation") or "答案来自采集页面。"
                if not existing.source_url:
                    existing.source_url = record.url
                stats.answers_filled += 1
            continue

        question = Question(
            subject_id=subject.id,
            content=content,
            question_type=question_type,
            options=options,
            answer=raw_answer.upper() if has_answer else PENDING_ANSWER_MARKER,
            answer_source=(
                AnswerSource.CRAWLED.value if has_answer else AnswerSource.PENDING.value
            ),
            explanation=item.get("explanation")
            or ("答案来自采集页面。" if has_answer else "采集正文已解析, 答案待补充。"),
            year=record.year,
            month=record.month,
            chapter_id=chapters[index % len(chapters)].id if chapters else None,
            difficulty="medium",
            frequency=1,
            score=item.get("score") or 2,
            source=source_label,
            source_url=record.url,
        )
        db.add(question)
        db.flush()
        question_ids.append(question.id)
        stats.questions_new += 1

    if not question_ids:
        record.status = "link_only"
        record.error_message = "解析结果全部为无效题目"
        return 0

    paper = (
        db.query(PastPaper)
        .filter(
            PastPaper.subject_id == subject.id,
            PastPaper.year == record.year,
            PastPaper.month == record.month,
            PastPaper.source == source_label,
        )
        .first()
    )
    if not paper:
        paper = PastPaper(
            subject_id=subject.id,
            name=f"{record.year}年{record.month or '?'}月 {subject.name} 真题(采集)",
            year=record.year,
            month=record.month,
            total_score=sum(item.get("score") or 2 for item in parsed),
            duration=150,
            question_ids=question_ids,
            paper_config={"source_url": record.url, "harvested": True},
            source=source_label,
            is_published=True,
        )
        db.add(paper)
        db.flush()
        stats.papers_new += 1

    record.parsed_question_count = len(question_ids)
    record.linked_paper_id = paper.id
    record.status = "parsed"
    record.error_message = None
    return len(question_ids)


# --------------------------------------------------------------------------
# 单个 (科目, 期次) 的采集
# --------------------------------------------------------------------------

def harvest_one(
    db,
    subject: Subject,
    year: int,
    month: int,
    stats: HarvestStats,
    *,
    max_per_channel: int = 3,
    max_extract: int = 2,
    dry_run: bool = False,
    verbose: bool = True,
    fast: bool = False,
) -> None:
    seen_urls: set[str] = set()
    seen_canonical: set[str] = set()
    channels = FAST_CHANNELS if fast else CHANNELS

    for channel, query in build_queries(subject.code, subject.name, year, month, channels=channels):
        try:
            results = search_client.unified_search(query, max_results=max_per_channel + 2)
        except Exception as exc:
            stats.notes.append(f"{channel} 搜索失败: {type(exc).__name__}")
            continue
        stats.searched += 1
        time.sleep(random.uniform(*DELAY_RANGE))

        # 站内搜索时过滤掉跑到别的域名的结果
        domain = dict((label, dom) for label, dom in channels).get(
            channel.replace("-全国", ""), ""
        )
        if domain:
            results = [r for r in results if domain in (urlparse(r.url or "").netloc or "")]

        # 全国卷优先排序
        results.sort(key=national_rank)

        extracted_here = 0
        for result in results[:max_per_channel]:
            url = (result.url or "").strip()
            if not url or url in seen_urls:
                continue
            # 归一化去重(同一文章的 PC/移动版)
            canon = canonical_url(url)
            if canon in seen_canonical:
                continue
            seen_urls.add(url)
            seen_canonical.add(canon)

            if dry_run:
                kind = media_type(result)
                if verbose:
                    print(f"    [dry] {kind:5s} {channel:10s} {url[:70]}")
                continue

            record, is_new = save_source_record(db, result, subject, year, month, query, channel)
            if is_new:
                stats.sources_new += 1
            # 已处理过的源不重复抽取
            if record.status in ("parsed", "link_only") and not is_new:
                continue
            if record.media_type == "video":
                continue
            if extracted_here >= max_extract:
                continue

            content, error = extract_content(result, record.media_type)
            extracted_here += 1
            time.sleep(random.uniform(*DELAY_RANGE))

            if not content:
                record.status = "link_only"
                record.error_message = error
                continue

            stats.extracted += 1
            record.content_text = content[:50000]
            record.status = "extracted"

            check = validate_paper_text(content)
            if not check.ok:
                record.status = "link_only"
                record.error_message = f"校验未通过: {check.reason}"
                if verbose:
                    print(f"    [skip] {channel:10s} {check.reason} {url[:52]}")
                continue

            stats.validated += 1
            count = import_parsed_questions(db, record, subject, stats)
            if verbose:
                flag = "答案页" if check.answer_count > 0 else "无答案"
                print(
                    f"    [ok]   {channel:10s} {flag} 解析{count}题 "
                    f"(选项{check.option_count}/答案{check.answer_count}) {url[:46]}"
                )

    if not dry_run:
        db.commit()


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def parse_periods(raw: str) -> list[tuple[int, int]]:
    """解析 '2024-10,2023-4' 或 'all' 为期次列表。"""
    if raw.strip().lower() == "all":
        # 2021年4月 ~ 2026年4月 (2026年10月尚未考试)
        periods = []
        for y in range(2021, 2027):
            for m in (4, 10):
                if y == 2026 and m == 10:
                    continue  # 未来期次
                periods.append((y, m))
        return periods
    periods = []
    for chunk in raw.split(","):
        chunk = chunk.strip()
        if not chunk:
            continue
        match = re.fullmatch(r"(20\d{2})[-/](4|10)", chunk)
        if not match:
            raise SystemExit(f"期次格式错误: {chunk} (应形如 2024-10)")
        periods.append((int(match.group(1)), int(match.group(2))))
    return periods


def is_done(db, subject_id: int, year: int, month: int) -> bool:
    """该 (科目, 期次) 是否已有采集过的 parsed 源记录。用于断点续跑。"""
    return (
        db.query(PastPaperSource)
        .filter(
            PastPaperSource.subject_id == subject_id,
            PastPaperSource.year == year,
            PastPaperSource.month == month,
            PastPaperSource.status == "parsed",
        )
        .count()
        > 0
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="多渠道真题采集")
    parser.add_argument("--subject", help="课程代码, 如 00277")
    parser.add_argument("--subjects", help="多个课程代码, 逗号分隔")
    parser.add_argument("--subjects-file", help="课程代码文件, 每行一个")
    parser.add_argument("--all", action="store_true", help="遍历库中所有科目")
    parser.add_argument("--year", type=int, help="年份(与 --month 配合)")
    parser.add_argument("--month", type=int, choices=[4, 10], help="月份")
    parser.add_argument("--periods", help="批量期次, 如 2024-10,2024-4")
    parser.add_argument("--limit-subjects", type=int, help="限制科目数(便于试跑)")
    parser.add_argument("--max-per-channel", type=int, default=3, help="每渠道取前 N 条结果")
    parser.add_argument("--max-extract", type=int, default=2, help="每渠道最多抽取 N 个页面")
    parser.add_argument("--fast", action="store_true", help="只用高产出渠道(搜狐+全网), 批量跑时推荐")
    parser.add_argument("--resume", action="store_true", help="跳过已有 parsed 源的 (科目,期次)")
    parser.add_argument("--dry-run", action="store_true", help="只搜索不入库")
    args = parser.parse_args()

    if args.periods:
        periods = parse_periods(args.periods)
    elif args.year and args.month:
        periods = [(args.year, args.month)]
    else:
        raise SystemExit("需指定 --year/--month 或 --periods (用 'all' 表示 2021-2026 全部期次)")

    db = SessionLocal()
    try:
        wanted_codes: list[str] = []
        if args.subject:
            wanted_codes = [args.subject.strip()]
        elif args.subjects:
            wanted_codes = [c.strip() for c in args.subjects.split(",") if c.strip()]
        elif args.subjects_file:
            path = Path(args.subjects_file)
            if not path.exists():
                raise SystemExit(f"科目文件不存在: {path}")
            wanted_codes = [
                line.strip()
                for line in path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.startswith("#")
            ]

        if wanted_codes:
            # 按给定顺序保持优先级
            found = {s.code: s for s in db.query(Subject).filter(Subject.code.in_(wanted_codes)).all()}
            subjects = [found[c] for c in wanted_codes if c in found]
            missing = [c for c in wanted_codes if c not in found]
            if missing:
                print(f"[警告] 库中无以下课程代码, 已跳过: {', '.join(missing)}")
            if not subjects:
                raise SystemExit("指定的课程代码在库中均不存在")
        elif args.all:
            subjects = db.query(Subject).order_by(Subject.code).all()
        else:
            raise SystemExit("需指定 --subject / --subjects / --subjects-file / --all")

        if args.limit_subjects:
            subjects = subjects[: args.limit_subjects]

        stats = HarvestStats()
        total = len(subjects) * len(periods)
        print(f"搜索源: {search_client.available_sources}")
        print(f"任务: {len(subjects)} 科目 x {len(periods)} 期次 = {total} 组")
        if args.fast:
            print(f"快速模式: 仅搜狐+全网 ({len(FAST_CHANNELS)} 渠道)")
        if args.resume:
            print("断点续跑: 跳过已有 parsed 源的组合")
        if args.dry_run:
            print("[dry-run] 不写数据库\n")

        done = 0
        skipped = 0
        for subject in subjects:
            for year, month in periods:
                done += 1
                if args.resume and is_done(db, subject.id, year, month):
                    skipped += 1
                    continue
                print(f"[{done}/{total}] {subject.code} {subject.name} {year}年{month}月")
                harvest_one(
                    db,
                    subject,
                    year,
                    month,
                    stats,
                    max_per_channel=args.max_per_channel,
                    max_extract=args.max_extract,
                    dry_run=args.dry_run,
                    fast=args.fast,
                )

        print("\n===== 采集汇总 =====")
        if skipped:
            print(f"  已跳过(续跑) : {skipped}")
        print(f"  搜索次数    : {stats.searched}")
        print(f"  新增源记录  : {stats.sources_new}")
        print(f"  成功抽取正文: {stats.extracted}")
        print(f"  通过真题校验: {stats.validated}")
        print(f"  新增题目    : {stats.questions_new}")
        print(f"  重复题目    : {stats.questions_dup}")
        print(f"  回填答案    : {stats.answers_filled}")
        print(f"  新增试卷    : {stats.papers_new}")
        if stats.notes:
            print("  异常:")
            for note in stats.notes[:8]:
                print(f"    - {note}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
