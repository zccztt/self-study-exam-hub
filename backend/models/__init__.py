# -*- coding: utf-8 -*-
"""SQLAlchemy model registry."""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .user import User  # noqa: E402
from .subject import Subject  # noqa: E402
from .chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint  # noqa: E402
from .question import Difficulty, Question, QuestionType  # noqa: E402
from .favorite import QuestionFavorite, VideoFavorite  # noqa: E402
from .exam import Exam, ExamSession, ExamMode, ExamStatus, WrongQuestion  # noqa: E402
from .video import Video, VideoKnowledgePoint, VideoQuestion, VideoSource  # noqa: E402
from .planner import DailyTask, StudyPlan, UserMastery  # noqa: E402

__all__ = [
    "Base",
    "User",
    "Subject",
    "Chapter",
    "KnowledgePoint",
    "QuestionKnowledgePoint",
    "Difficulty",
    "Question",
    "QuestionType",
    "QuestionFavorite",
    "VideoFavorite",
    "Exam",
    "ExamSession",
    "ExamMode",
    "ExamStatus",
    "WrongQuestion",
    "Video",
    "VideoKnowledgePoint",
    "VideoQuestion",
    "VideoSource",
    "DailyTask",
    "StudyPlan",
    "UserMastery",
]
