# -*- coding: utf-8 -*-
"""Question model."""

import enum

from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.sql import func

from backend.models import Base


# 答案缺失的占位标记。带此标记的题目可用于题库浏览和练习，但不参与需要评分的考试。
PENDING_ANSWER_MARKER = "待核实"


class AnswerSource(str, enum.Enum):
    """答案来源，用于区分答案可信度。"""

    CRAWLED = "crawled"              # 采集时即带答案
    STEM_EXTRACTED = "stem_extracted"  # 从题干误拼的字母中恢复
    DB_MATCHED = "db_matched"        # 由库内重复题互补得到
    PENDING = "pending"              # 答案缺失


class QuestionType(str, enum.Enum):
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CASE = "case"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(Base):
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True)
    content = Column(Text, nullable=False)
    question_type = Column(String(32), nullable=False, index=True)
    options = Column(JSON)
    answer = Column(Text, nullable=False)
    explanation = Column(Text)
    year = Column(Integer, index=True)
    month = Column(Integer)
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True)
    difficulty = Column(String(20), default=Difficulty.MEDIUM.value, index=True)
    frequency = Column(Integer, default=1, nullable=False)
    score = Column(Integer, default=2, nullable=False)
    source = Column(String(200))
    source_url = Column(String(500))
    answer_source = Column(
        String(20),
        default="crawled",
        index=True,
        comment="答案来源: crawled/stem_extracted/db_matched/pending",
    )
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Question {self.id} - {self.question_type}>"
