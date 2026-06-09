# -*- coding: utf-8 -*-
"""Parse raw exam papers into the JSON format consumed by data_import.py."""

from __future__ import annotations

import argparse
import json
import re
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from xml.etree import ElementTree


QUESTION_PATTERN = re.compile(r"^\s*(\d+)[\.、．)]\s*(.+)")
OPTION_PATTERN = re.compile(r"^\s*([A-F])[\.\)、．]\s*(.+)", re.I)
ANSWER_PATTERN = re.compile(r"^\s*(答案|参考答案|正确答案)[:：]\s*(.+)")
EXPLANATION_PATTERN = re.compile(r"^\s*(解析|答案解析|说明)[:：]\s*(.+)")


def read_paper_text(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return path.read_text(encoding="utf-8")
    if suffix == ".docx":
        return read_docx_text(path)
    if suffix == ".pdf":
        return read_pdf_text(path)
    raise ValueError("Only .txt, .md, .docx and .pdf files are supported.")


def read_docx_text(path: Path) -> str:
    with zipfile.ZipFile(path) as archive:
        xml_content = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_content)
    namespace = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
    paragraphs = []
    for paragraph in root.findall(".//w:p", namespace):
        texts = [node.text or "" for node in paragraph.findall(".//w:t", namespace)]
        if texts:
            paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def read_pdf_text(path: Path) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise RuntimeError("PDF parsing requires installing pypdf, or convert the PDF to text first.") from exc

    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def parse_paper_text(
    text: str,
    *,
    subject_code: str,
    subject_name: str,
    year: Optional[int],
    month: Optional[int],
    source: str,
    default_difficulty: str,
) -> List[Dict[str, Any]]:
    questions: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    explanation_mode = False

    def finish_current() -> None:
        if not current:
            return
        content = "\n".join(current.pop("_content_lines", [])).strip()
        if not content:
            return
        options = current.get("options") or []
        answer = str(current.get("answer") or "").strip()
        question_type = infer_question_type(options, answer)
        current.update(
            {
                "subject_code": subject_code,
                "subject_name": subject_name,
                "content": content,
                "question_type": question_type,
                "difficulty": current.get("difficulty") or default_difficulty,
                "score": current.get("score") or default_score(question_type),
                "year": year,
                "month": month,
                "source": source,
                "review_status": "pending",
            }
        )
        questions.append(dict(current))

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        question_match = QUESTION_PATTERN.match(line)
        if question_match:
            finish_current()
            current = {
                "_content_lines": [question_match.group(2).strip()],
                "options": [],
                "answer": "",
                "explanation": "",
                "knowledge_points": [],
            }
            explanation_mode = False
            continue

        if current is None:
            continue

        option_match = OPTION_PATTERN.match(line)
        if option_match:
            current.setdefault("options", []).append(option_match.group(2).strip())
            explanation_mode = False
            continue

        answer_match = ANSWER_PATTERN.match(line)
        if answer_match:
            current["answer"] = normalize_answer(answer_match.group(2))
            explanation_mode = False
            continue

        explanation_match = EXPLANATION_PATTERN.match(line)
        if explanation_match:
            current["explanation"] = explanation_match.group(2).strip()
            explanation_mode = True
            continue

        if explanation_mode:
            current["explanation"] = f"{current.get('explanation') or ''}\n{line}".strip()
        else:
            current.setdefault("_content_lines", []).append(line)

    finish_current()
    return questions


def normalize_answer(value: str) -> str:
    cleaned = re.sub(r"\s+", "", value.strip())
    return cleaned.strip("。；;")


def infer_question_type(options: List[str], answer: str) -> str:
    if options:
        letters = re.sub(r"[^A-F]", "", answer.upper())
        return "multiple_choice" if len(letters) > 1 else "single_choice"
    if re.search(r"_{2,}|（\s*）|\(\s*\)", answer):
        return "fill_blank"
    return "short_answer"


def default_score(question_type: str) -> int:
    return {
        "single_choice": 2,
        "multiple_choice": 2,
        "fill_blank": 2,
        "short_answer": 6,
        "essay": 10,
        "case": 10,
    }.get(question_type, 2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse a raw exam paper into importable JSON.")
    parser.add_argument("--input", required=True, type=Path, help="Raw paper path: txt, md, docx, or pdf.")
    parser.add_argument("--output", required=True, type=Path, help="Output JSON path.")
    parser.add_argument("--subject-code", required=True)
    parser.add_argument("--subject-name", required=True)
    parser.add_argument("--year", type=int)
    parser.add_argument("--month", type=int)
    parser.add_argument("--source", default="原始真题解析导入")
    parser.add_argument("--default-difficulty", default="medium", choices=["easy", "medium", "hard"])
    args = parser.parse_args()

    text = read_paper_text(args.input)
    questions = parse_paper_text(
        text,
        subject_code=args.subject_code,
        subject_name=args.subject_name,
        year=args.year,
        month=args.month,
        source=args.source,
        default_difficulty=args.default_difficulty,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(questions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Parsed {len(questions)} questions -> {args.output}")


if __name__ == "__main__":
    main()
