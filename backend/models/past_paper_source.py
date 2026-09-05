# -*- coding: utf-8 -*-
"""Raw source records for real-paper ingestion and deferred review."""

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.sql import func

from backend.models import Base


class PastPaperSource(Base):
    __tablename__ = "past_paper_sources"
    __table_args__ = (UniqueConstraint("url", name="uq_past_paper_sources_url"),)

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True, index=True)
    year = Column(Integer, nullable=True, index=True)
    month = Column(Integer, nullable=True, index=True)
    title = Column(String(300), nullable=False)
    url = Column(String(1000), nullable=False)
    source = Column(String(100), nullable=False, index=True)
    media_type = Column(String(20), nullable=False, default="html")  # pdf/image/video/html
    status = Column(String(30), nullable=False, default="pending")  # parsed/link_only/failed
    local_path = Column(String(500), nullable=True)
    content_text = Column(Text, nullable=True)
    parsed_question_count = Column(Integer, nullable=False, default=0)
    linked_paper_id = Column(Integer, ForeignKey("past_papers.id"), nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    def __repr__(self) -> str:
        return f"<PastPaperSource {self.id} {self.media_type}/{self.status}>"
