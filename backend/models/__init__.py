# -*- coding: utf-8 -*-
"""SQLAlchemy model registry."""

from sqlalchemy.orm import declarative_base

Base = declarative_base()

from .user import User  # noqa: E402
from .subject import Subject  # noqa: E402
from .chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint  # noqa: E402
from .question import Difficulty, Question, QuestionType  # noqa: E402
from .favorite import QuestionFavorite, VideoFavorite  # noqa: E402
from .exam import Exam, ExamResult, ExamSession, ExamMode, ExamStatus, WrongQuestion  # noqa: E402
from .video import Video, VideoKnowledgePoint, VideoQuestion, VideoSource  # noqa: E402
from .planner import DailyTask, StudyPlan, UserMastery  # noqa: E402
from .feedback import GradingFeedback  # noqa: E402
from .knowledge import UserDocument  # noqa: E402
from .flashcard import Flashcard  # noqa: E402
from .enrollment import (  # noqa: E402
    Major,
    MajorSubject,
    Province,
    School,
    UserEnrollment,
    UserSubjectStatus,
)
from .crawl_log import CrawlLog  # noqa: E402
from .past_paper import PastPaper  # noqa: E402
from .past_paper_source import PastPaperSource  # noqa: E402
from .resource import PaperSourceResource, QuestionResource, Resource  # noqa: E402
from .exam_schedule import ExamSchedule  # noqa: E402
from .ai_provider import AIProvider, SearchProvider, UserProviderConfig  # noqa: E402

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
    "ExamResult",
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
    "GradingFeedback",
    "UserDocument",
    "Flashcard",
    "Province",
    "School",
    "Major",
    "MajorSubject",
    "UserEnrollment",
    "UserSubjectStatus",
    "CrawlLog",
    "PastPaper",
    "PastPaperSource",
    "Resource",
    "QuestionResource",
    "PaperSourceResource",
    "ExamSchedule",
    "AIProvider",
    "SearchProvider",
    "UserProviderConfig",
]
