# -*- coding: utf-8 -*-
"""知识库服务 - 简易 RAG 实现，将本地知识点注入 AI prompt 上下文。"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.question import Question


class KnowledgeService:
    """从数据库和本地知识库文件加载相关知识点，用于 RAG 注入。"""

    KNOWLEDGE_BASE_DIR = Path(__file__).parent.parent / "data" / "knowledge_base"

    def __init__(self, db: Session):
        self.db = db
        self._file_cache: Dict[str, str] = {}

    def get_context_for_question(self, question: Question) -> str:
        """为指定题目获取相关知识上下文，用于注入 AI 评分 prompt。

        返回格式化的知识点文本，AI 可据此评分而非凭空生成。
        """
        contexts: List[str] = []

        # 1. 从数据库获取关联知识点
        linked_points = (
            self.db.query(KnowledgePoint)
            .join(
                QuestionKnowledgePoint,
                QuestionKnowledgePoint.knowledge_point_id == KnowledgePoint.id,
            )
            .filter(QuestionKnowledgePoint.question_id == question.id)
            .all()
        )
        for kp in linked_points:
            if kp.description:
                contexts.append(f"【知识点：{kp.name}】{kp.description}")

        # 2. 从本地 JSON 知识库文件加载补充内容
        file_context = self._load_from_files(question.subject_id, question.chapter_id)
        if file_context:
            contexts.append(file_context)

        # 3. 从用户上传文档中提取相关内容
        user_context = self._load_from_user_documents(question.subject_id)
        if user_context:
            contexts.append(user_context)

        if not contexts:
            return ""
        return "\n\n--- 相关知识点（评分时必须参考） ---\n" + "\n".join(contexts)

    def get_context_for_subject(self, subject_id: int, point_names: List[str]) -> str:
        """为指定科目的考点列表获取知识上下文，用于注入分析 prompt。"""
        contexts: List[str] = []
        # KnowledgePoint 没有 subject_id，需要通过 Chapter 关联
        points = (
            self.db.query(KnowledgePoint)
            .join(Chapter, Chapter.id == KnowledgePoint.chapter_id)
            .filter(
                Chapter.subject_id == subject_id,
                KnowledgePoint.name.in_(point_names),
            )
            .all()
        )
        for kp in points:
            if kp.description:
                contexts.append(f"【{kp.name}】{kp.description}")

        if not contexts:
            return ""
        return "\n\n--- 知识库参考（分析时必须基于以下内容） ---\n" + "\n".join(contexts[:10])

    def _load_from_files(self, subject_id: Optional[int], chapter_id: Optional[int]) -> str:
        """从本地 JSON 文件加载知识库内容。"""
        if not self.KNOWLEDGE_BASE_DIR.exists():
            return ""

        cache_key = f"{subject_id}_{chapter_id}"
        if cache_key in self._file_cache:
            return self._file_cache[cache_key]

        result = ""
        # 按科目查找知识库文件
        for json_file in self.KNOWLEDGE_BASE_DIR.glob("*.json"):
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    continue
                if data.get("subject_id") != subject_id:
                    continue
                # 提取章节相关知识
                chapters = data.get("chapters", [])
                for chapter in chapters:
                    if chapter_id and chapter.get("chapter_id") != chapter_id:
                        continue
                    points = chapter.get("knowledge_points", [])
                    for point in points[:5]:  # 限制注入量
                        name = point.get("name", "")
                        desc = point.get("description", "")
                        if name and desc:
                            result += f"\n【{name}】{desc}"
            except (json.JSONDecodeError, OSError):
                continue

        self._file_cache[cache_key] = result
        return result

    def _load_from_user_documents(self, subject_id: Optional[int]) -> str:
        """从用户上传的文档中加载相关内容片段。"""
        try:
            from backend.models.knowledge import UserDocument
        except ImportError:
            return ""

        if not subject_id:
            return ""

        docs = (
            self.db.query(UserDocument)
            .filter(
                UserDocument.subject_id == subject_id,
                UserDocument.content_text.isnot(None),
            )
            .limit(3)
            .all()
        )
        if not docs:
            return ""

        snippets: List[str] = []
        for doc in docs:
            text = (doc.content_text or "")[:2000]  # 每篇限 2000 字
            if text:
                snippets.append(f"【用户资料：{doc.filename}】{text}")

        if not snippets:
            return ""
        return "\n".join(snippets)
