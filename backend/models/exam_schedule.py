# -*- coding: utf-8 -*-
"""考试日程模型 - 从河北教育考试院爬取的真实考试时间"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Date, DateTime, Text
from . import Base


class ExamSchedule(Base):
    """考试日程表 - 报名时间、考试时间、成绩发布时间"""

    __tablename__ = "exam_schedules"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 考期标识，如 "2026年10月"
    exam_period = Column(String(50), nullable=False, index=True, comment="考期，如2026年10月")

    # 报名时间
    register_start = Column(Date, nullable=True, comment="报名开始日期")
    register_end = Column(Date, nullable=True, comment="报名结束日期")

    # 考试时间
    exam_start = Column(Date, nullable=False, comment="考试开始日期")
    exam_end = Column(Date, nullable=True, comment="考试结束日期（多日考试）")

    # 成绩发布时间
    result_date = Column(Date, nullable=True, comment="成绩发布日期")

    # 备注说明
    note = Column(Text, nullable=True, comment="备注，如考试时间段、注意事项等")

    # 数据来源
    source_url = Column(String(500), nullable=True, comment="数据来源URL")
    crawled_at = Column(DateTime, nullable=False, default=datetime.utcnow, comment="爬取时间")

    # 是否已过期
    is_past = Column(Integer, default=0, comment="0未过期 1已过期")

    def __repr__(self):
        return f"<ExamSchedule {self.exam_period} exam:{self.exam_start}>"
