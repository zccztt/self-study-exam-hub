# -*- coding: utf-8 -*-
"""Enrollment models: Province, School, Major, and user enrollment tracking."""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.sql import func

from backend.models import Base


class Province(Base):
    """自考省份/地区"""
    __tablename__ = "provinces"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(10), unique=True, nullable=False, index=True)  # e.g. "44"
    name = Column(String(50), nullable=False)  # e.g. "广东省"
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<Province {self.code} - {self.name}>"


class School(Base):
    """主考院校"""
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=False, index=True)
    code = Column(String(20))  # 院校代码
    logo_url = Column(String(500))
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<School {self.name}>"


class Major(Base):
    """专业计划（省+院校+层次维度）"""
    __tablename__ = "majors"
    __table_args__ = (
        Index("ix_majors_province_school", "province_id", "school_id"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, index=True)  # 专业代码 e.g. "120201K"
    name = Column(String(100), nullable=False)  # e.g. "工商管理"
    level = Column(String(20), nullable=False)  # zk(专科) / bk(本科)
    province_id = Column(Integer, ForeignKey("provinces.id"), nullable=False)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=False)
    total_credits = Column(Integer)  # 毕业学分要求
    description = Column(Text)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Major {self.code} - {self.name}>"


class MajorSubject(Base):
    """专业-科目关联（考试计划中的每一门课）"""
    __tablename__ = "major_subjects"
    __table_args__ = (
        UniqueConstraint("major_id", "subject_id", name="uq_major_subjects"),
        Index("ix_major_subjects_major", "major_id"),
        Index("ix_major_subjects_subject", "subject_id"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    course_type = Column(String(20), nullable=False)  # required(必考), elective(选考), additional(加考)
    credits = Column(Float)  # 学分
    sort_order = Column(Integer, default=0)  # 推荐考试顺序

    def __repr__(self) -> str:
        return f"<MajorSubject major={self.major_id} subject={self.subject_id}>"


class UserEnrollment(Base):
    """用户报考注册（绑定目标专业）"""
    __tablename__ = "user_enrollments"
    __table_args__ = (
        UniqueConstraint("user_id", "major_id", name="uq_user_enrollment"),
        Index("ix_user_enrollments_user", "user_id"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    major_id = Column(Integer, ForeignKey("majors.id"), nullable=False)
    target_date = Column(Date)  # 目标毕业日期
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserEnrollment U{self.user_id} M{self.major_id}>"


class UserSubjectStatus(Base):
    """用户科目考试状态标记"""
    __tablename__ = "user_subject_status"
    __table_args__ = (
        UniqueConstraint("user_id", "subject_id", "enrollment_id", name="uq_user_subject_status"),
        Index("ix_user_subject_status_user", "user_id"),
        Index("ix_user_subject_status_enrollment", "enrollment_id"),
        {},
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    enrollment_id = Column(Integer, ForeignKey("user_enrollments.id"), nullable=False)
    status = Column(String(20), default="not_taken", nullable=False)  # not_taken / passed / failed
    score = Column(Float, nullable=True)  # 考试成绩
    exam_date = Column(Date, nullable=True)  # 考试日期
    attempt_count = Column(Integer, default=0, nullable=False)  # 考试次数
    certificate_no = Column(String(50))  # 合格证书编号
    note = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<UserSubjectStatus U{self.user_id} S{self.subject_id} {self.status}>"
