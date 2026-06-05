# -*- coding: utf-8 -*-
"""
学习规划模型
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Boolean, JSON, Float
from sqlalchemy.sql import func
from backend.models import Base


class StudyPlan(Base):
    """学习计划表"""
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True, comment="计划ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    exam_date = Column(DateTime(timezone=True), nullable=False, comment="考试日期")
    daily_hours = Column(Float, nullable=False, comment="每日学习时长（小时）")
    subjects = Column(JSON, nullable=False, comment="报考科目ID列表")
    preferences = Column(JSON, comment="学习偏好配置")
    status = Column(String(20), default="active", index=True, comment="计划状态（active/completed/abandoned）")
    completion_rate = Column(Float, default=0.0, comment="完成率")
    expected_pass_rate = Column(Float, comment="预计通过率")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<StudyPlan {self.id} - U{self.user_id}>"


class DailyTask(Base):
    """每日学习任务表"""
    __tablename__ = "daily_tasks"

    id = Column(Integer, primary_key=True, index=True, comment="任务ID")
    plan_id = Column(Integer, ForeignKey("study_plans.id"), nullable=False, index=True, comment="计划ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    task_date = Column(DateTime(timezone=True), nullable=False, index=True, comment="任务日期")
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False, comment="科目ID")
    chapter_ids = Column(JSON, comment="章节ID列表")
    question_count = Column(Integer, default=0, comment="刷题数量")
    video_ids = Column(JSON, comment="视频ID列表")
    review_points = Column(JSON, comment="复习知识点列表")
    is_completed = Column(Boolean, default=False, comment="是否完成")
    actual_hours = Column(Float, comment="实际学习时长")
    completion_time = Column(DateTime(timezone=True), comment="完成时间")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<DailyTask {self.id} - {self.task_date.date()}>"


class UserMastery(Base):
    """用户知识点掌握度表"""
    __tablename__ = "user_mastery"

    id = Column(Integer, primary_key=True, index=True, comment="ID")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True, comment="用户ID")
    knowledge_point_id = Column(Integer, ForeignKey("knowledge_points.id"), nullable=False, index=True, comment="知识点ID")
    mastery_level = Column(Float, default=0.0, comment="掌握度（0.0-1.0）")
    correct_count = Column(Integer, default=0, comment="正确次数")
    wrong_count = Column(Integer, default=0, comment="错误次数")
    last_practice_time = Column(DateTime(timezone=True), comment="最后练习时间")
    next_review_time = Column(DateTime(timezone=True), comment="下次复习时间（遗忘曲线）")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), comment="更新时间")

    def __repr__(self):
        return f"<UserMastery U{self.user_id}-KP{self.knowledge_point_id}>"
