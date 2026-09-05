# -*- coding: utf-8 -*-
"""CrawlLog model: tracks each crawl run for versioning and monitoring."""

from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.sql import func

from backend.models import Base


class CrawlLog(Base):
    """Records each crawl run for audit and change detection."""
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String(50), nullable=False, index=True)  # e.g. "zikaosw"
    province_code = Column(String(10), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="running")  # running / success / failed
    schools_found = Column(Integer, default=0)
    majors_found = Column(Integer, default=0)
    majors_created = Column(Integer, default=0)
    majors_updated = Column(Integer, default=0)
    courses_found = Column(Integer, default=0)
    links_created = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    errors = Column(JSON)  # list of error messages
    duration_seconds = Column(Integer)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self) -> str:
        return f"<CrawlLog {self.source}/{self.province_code} {self.status}>"
