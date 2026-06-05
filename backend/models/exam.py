# -*- coding: utf-8 -*-
"""
考试相关模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
import enum
from backend.models import Base


class ExamMode(str, enum.Enum):
    """考试模式枚举"""
    REAL_EXAM = "real_exam"  # 真题卷
    RANDOM = "random"  # 随机组卷
    CHAPTER = "chapter"  # 章节练习
    WRONG_QUESTIONS = "wrong_questions"  # 错题重做


class ExamStatus(str, enum.Enum):
    """考试状态枚举"""
    IN_PROGRESS = "in_progress"  # 进行中
    COMPLETED = "completed"  # 已完成
    TIMEOUT = "timeout"  # 超时


class Exam(Base):
    """试卷表"""
    __tablename__ = "exams"

    id = Column(Integer, primary_key=True, index=True, comment="试卷ID")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, index=True, comment="科目ID")
    name = Column(String(200), nullable=False, comment="试卷名称")
    mode = Column(SQLEnum(ExamMode), nullable=False, comment="考试模式")
    year = Column(Integer, comment="年份（真题卷）")
    month = Column(Integer, comment="月份（真题卷）")
    duration = Column(Integer, default=150, comment="考试时长（分钟）")
    total_score = Column(Integer, default=100, comment="总分")
    config = Column(JSON, comment="组卷配置（章节、题型、难度等）")
    question_ids = Column(JSON, nullable=False, comment="题目ID列表")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<Exam {self.id} - {self.name}>"


class ExamSession(Base):
    """考试会话表"""
    __tablename__ = "exam_sessions"

    id = Column(Integer, primary_key=True, index=True, comment="会话ID")
    session_id = Column(String(100), unique=True, nullable=False, index=True, comment="会话唯一标识")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    exam_id = Column(Integer, ForeignKey("exams.id"), nullable=False, index=True, comment="试卷ID")
    status = Column(SQLEnum(ExamStatus), default=ExamStatus.IN_PROGRESS, index=True, comment="考试状态")
    answers = Column(JSON, default={}, comment="用户答案（question_id: answer）")
    score = Column(Integer, comment="得分")
    correct_count = Column(Integer, comment="正确题数")
    total_count = Column(Integer, comment="总题数")
    start_time = Column(DateTime(timezone=True), server_default=func.now(), comment="开始时间")
    end_time = Column(DateTime(timezone=True), comment="结束时间")
    submit_time = Column(DateTime(timezone=True), comment="提交时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<ExamSession {self.session_id}>"


class WrongQuestion(Base):
    """错题本表"""
    __tablename__ = "wrong_questions"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    question_id = Column(Integer, ForeignKey("questions.id"), nullable=False, index=True, comment="题目ID")
    session_id = Column(Integer, ForeignKey("exam_sessions.id"), comment="来源会话ID")
    user_answer = Column(Text, comment="用户答案")
    wrong_count = Column(Integer, default=1, comment="错误次数")
    is_mastered = Column(Boolean, default=False, comment="是否已掌握")
    tags = Column(JSON, comment="自定义标签")
    note = Column(Text, comment="笔记")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<WrongQuestion U{self.user_id}-Q{self.question_id}>"
