# -*- coding: utf-8 -*-
"""User model."""

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(100))
    is_active = Column(Boolean, default=True, nullable=False)
    is_superuser = Column(Boolean, default=False, nullable=False)

    # Extended profile fields
    current_job = Column(String(100), nullable=True, comment="当前职业")
    education_background = Column(String(100), nullable=True, comment="学历背景，如高中/大专/本科")
    education_major = Column(String(100), nullable=True, comment="原专业方向")
    skills = Column(Text, nullable=True, comment="技能标签，逗号分隔")
    study_hours_per_day = Column(Integer, nullable=True, comment="每日可用学习时间(小时)")
    exam_experience = Column(String(50), nullable=True, comment="自考经验: none/beginner/experienced")
    learning_preference = Column(String(50), nullable=True, comment="学习偏好: video/reading/practice")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<User {self.username}>"
