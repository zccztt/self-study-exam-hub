# -*- coding: utf-8 -*-
"""
题目模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import ARRAY
import enum
from backend.models import Base


class QuestionType(str, enum.Enum):
    """题型枚举"""
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    FILL_BLANK = "fill_blank"
    SHORT_ANSWER = "short_answer"
    ESSAY = "essay"
    CASE = "case"


class Difficulty(str, enum.Enum):
    """难度枚举"""
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Question(Base):
    """题目表"""
    __tablename__ = "questions"

    id = Column(Integer, primary_key=True, index=True, comment="题目ID")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True, comment="科目ID")
    content = Column(Text, nullable=False, comment="题目内容")
    type = Column(SQLEnum(QuestionType), nullable=False, index=True, comment="题型")
    options = Column(ARRAY(String), comment="选项（JSON数组）")
    answer = Column(Text, nullable=False, comment="正确答案")
    explanation = Column(Text, comment="答案解析")
    year = Column(Integer, index=True, comment="年份")
    month = Column(Integer, comment="月份")
    chapter_id = Column(Integer, ForeignKey("chapters.id"), index=True, comment="章节ID")
    difficulty = Column(SQLEnum(Difficulty), default=Difficulty.MEDIUM, index=True, comment="难度")
    frequency = Column(Integer, default=1, comment="出现次数")
    score = Column(Integer, default=2, comment="分值")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Question {self.id} - {self.type.value}>"
