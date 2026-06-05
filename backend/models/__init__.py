# -*- coding: utf-8 -*-
"""
数据模型模块
"""

from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# 导入所有模型
from .user import User
from .subject import Subject
from .question import Question
from .chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from .exam import Exam, ExamSession, WrongQuestion
from .video import Video, VideoKnowledgePoint, VideoQuestion
from .planner import StudyPlan, DailyTask, UserMastery

__all__ = [
    'Base',
    'User',
    'Subject',
    'Question',
    'Chapter',
    'KnowledgePoint',
    'QuestionKnowledgePoint',
    'Exam',
    'ExamSession',
    'WrongQuestion',
    'Video',
    'VideoKnowledgePoint',
    'VideoQuestion',
    'StudyPlan',
    'DailyTask',
    'UserMastery',
]
