# -*- coding: utf-8 -*-
"""Subject model."""

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    category = Column(String(50), default="public")
    description = Column(Text)
    exam_duration = Column(Integer, default=150, nullable=False)
    total_score = Column(Integer, default=100, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<Subject {self.code} - {self.name}>"
