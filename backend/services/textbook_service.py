# -*- coding: utf-8 -*-
"""教材服务 - 为 AI 出题和评分提供教材内容上下文。"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TextbookService:
    """加载课程教材内容，为 AI 生成题目和评分提供权威参考。

    教材文件存放在 backend/data/textbooks/{course_code}.txt 或 .json
    - .txt: 纯文本教材内容（章节用 # 标记）
    - .json: 结构化教材 {"chapters": [{"title": ..., "sections": [...], "content": ...}]}
    """

    TEXTBOOK_DIR = Path(__file__).parent.parent / "data" / "textbooks"
    KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "data" / "knowledge_base"
    # 每次注入的最大字符数（控制 token 消耗）
    MAX_CONTEXT_CHARS = 3000

    def __init__(self) -> None:
        self._cache: Dict[str, Optional[str]] = {}

    def get_textbook_context(
        self,
        course_code: str,
        topic: Optional[str] = None,
        chapter_name: Optional[str] = None,
        max_chars: Optional[int] = None,
    ) -> str:
        """获取与主题相关的教材内容片段。

        Args:
            course_code: 课程代码（如 '15043'）
            topic: 搜索主题/关键词
            chapter_name: 指定章节名
            max_chars: 最大返回字符数

        Returns:
            相关教材内容文本，无内容时返回空字符串。
        """
        max_chars = max_chars or self.MAX_CONTEXT_CHARS
        content = self._load_textbook(course_code)
        if not content:
            return ""

        # 如果有章节名，先定位章节
        if chapter_name:
            chapter_content = self._extract_chapter(content, chapter_name)
            if chapter_content:
                content = chapter_content

        # 如果有主题，提取相关段落
        if topic:
            relevant = self._extract_relevant_paragraphs(content, topic, max_chars)
            if relevant:
                return relevant

        # 无法精确匹配时返回前 N 字符
        return content[:max_chars]

    def has_textbook(self, course_code: str) -> bool:
        """检查是否有指定课程的教材文件。"""
        return bool(self._load_textbook(course_code))

    def _load_textbook(self, course_code: str) -> Optional[str]:
        """加载教材内容（带缓存）。"""
        code = (course_code or "").strip()
        if not code:
            return None

        if code in self._cache:
            return self._cache[code]

        content = None
        txt_path = self.TEXTBOOK_DIR / f"{code}.txt"
        json_path = self.TEXTBOOK_DIR / f"{code}.json"

        if txt_path.exists():
            try:
                content = txt_path.read_text(encoding="utf-8")
            except OSError as exc:
                logger.warning("Failed to read textbook %s: %s", txt_path, exc)
        elif json_path.exists():
            try:
                data = json.loads(json_path.read_text(encoding="utf-8"))
                content = self._flatten_json_textbook(data)
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load textbook JSON %s: %s", json_path, exc)

        # 当前项目附带的知识点 JSON 是课程摘要，不是完整电子教材；
        # 仅作为 AI 参考上下文的安全回退，避免把摘要误标为教材全文。
        if not content:
            knowledge_path = self.KNOWLEDGE_BASE_DIR / f"{code}.json"
            if knowledge_path.exists():
                try:
                    data = json.loads(knowledge_path.read_text(encoding="utf-8"))
                    content = self._flatten_knowledge_summary(data)
                except (json.JSONDecodeError, OSError) as exc:
                    logger.warning("Failed to load knowledge base %s: %s", knowledge_path, exc)

        # Only cache successful loads; transient errors should allow retry.
        if content is not None:
            self._cache[code] = content
        return content

    @staticmethod
    def _flatten_json_textbook(data: dict) -> str:
        """将结构化 JSON 教材展平为文本。"""
        parts: List[str] = []
        for chapter in data.get("chapters", []):
            title = chapter.get("title", "")
            if title:
                parts.append(f"# {title}")
            for section in chapter.get("sections", []):
                section_title = section.get("title", "")
                section_content = section.get("content", "")
                if section_title:
                    parts.append(f"## {section_title}")
                if section_content:
                    parts.append(section_content)
            chapter_content = chapter.get("content", "")
            if chapter_content:
                parts.append(chapter_content)
        return "\n\n".join(parts)

    @staticmethod
    def _flatten_knowledge_summary(data: dict) -> str:
        parts: List[str] = [
            f"[课程教材/考点摘要，非完整电子教材] {data.get('textbook', '')}".strip()
        ]
        for chapter in data.get("chapters", []):
            title = chapter.get("name") or chapter.get("title") or ""
            if title:
                parts.append(f"# {title}")
            for point in chapter.get("knowledge_points", []):
                name = point.get("name", "")
                description = point.get("description", "")
                if name or description:
                    parts.append(f"## {name}\n{description}".strip())
        return "\n\n".join(item for item in parts if item)

    @staticmethod
    def _extract_chapter(content: str, chapter_name: str) -> str:
        """从文本中提取指定章节内容。"""
        # 匹配 # 章节名 到下一个 # 之间的内容
        pattern = re.compile(
            rf"^#\s*.*?{re.escape(chapter_name)}.*?$(.+?)(?=^#\s|\Z)",
            re.MULTILINE | re.DOTALL,
        )
        match = pattern.search(content)
        if match:
            return match.group(1).strip()
        # 退化为简单关键词定位
        idx = content.find(chapter_name)
        if idx >= 0:
            return content[idx : idx + 5000]
        return ""

    @staticmethod
    def _extract_relevant_paragraphs(content: str, topic: str, max_chars: int) -> str:
        """提取与主题相关的段落。"""
        keywords = [kw.strip() for kw in re.split(r"[,，\s]+", topic) if kw.strip()]
        if not keywords:
            return ""

        # 按段落分割
        paragraphs = re.split(r"\n{2,}", content)
        scored: List[tuple] = []
        for para in paragraphs:
            if len(para.strip()) < 20:
                continue
            score = sum(1 for kw in keywords if kw in para)
            if score > 0:
                scored.append((score, para.strip()))

        # 按相关度排序，拼接到不超过 max_chars
        scored.sort(key=lambda x: x[0], reverse=True)
        result_parts: List[str] = []
        total = 0
        for _, para in scored:
            if total + len(para) > max_chars:
                break
            result_parts.append(para)
            total += len(para)

        return "\n\n".join(result_parts)
