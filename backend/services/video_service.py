# -*- coding: utf-8 -*-
"""Video resource service."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.models.favorite import VideoFavorite
from backend.models.question import Question
from backend.models.video import Video, VideoQuestion


class VideoService:
    def __init__(self, db: Session):
        self.db = db

    def search_videos(
        self,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        chapter_ids: Optional[List[int]] = None,
        source: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = self.db.query(Video).filter(Video.is_active == 1)

        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(or_(Video.title.ilike(pattern), Video.description.ilike(pattern)))
        if subject_id:
            query = query.filter(Video.subject_id == subject_id)
        if chapter_ids:
            query = query.filter(Video.chapter_id.in_(chapter_ids))
        if source:
            query = query.filter(Video.source == source)

        total = query.count()
        videos = (
            query.order_by(Video.view_count.desc(), Video.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_video(video) for video in videos],
        }

    def get_video_detail(self, video_id: int) -> Optional[Dict[str, Any]]:
        video = self.db.query(Video).filter(Video.id == video_id, Video.is_active == 1).first()
        if not video:
            return None
        data = self._serialize_video(video)
        data["related_questions"] = self.get_related_questions(video_id)
        return data

    def get_related_questions(self, video_id: int) -> List[Dict[str, Any]]:
        questions = (
            self.db.query(Question)
            .join(VideoQuestion, Question.id == VideoQuestion.question_id)
            .filter(VideoQuestion.video_id == video_id)
            .all()
        )
        return [
            {
                "id": question.id,
                "content": question.content,
                "question_type": question.question_type,
                "year": question.year,
                "score": question.score,
            }
            for question in questions
        ]

    @staticmethod
    def validate_video_link(video_url: str) -> Dict[str, Any]:
        valid = video_url.startswith(("http://", "https://"))
        return {"valid": valid, "message": "Valid URL." if valid else "URL must start with http:// or https://."}

    def add_video(self, video_data: Dict[str, Any]) -> int:
        video = Video(**video_data)
        self.db.add(video)
        self.db.commit()
        self.db.refresh(video)
        return int(video.id)

    def add_to_favorites(self, user_id: int, video_id: int, note: Optional[str] = None) -> bool:
        video = self.db.query(Video).filter(Video.id == video_id, Video.is_active == 1).first()
        if not video:
            return False

        favorite = (
            self.db.query(VideoFavorite)
            .filter(and_(VideoFavorite.user_id == user_id, VideoFavorite.video_id == video_id))
            .first()
        )
        if favorite:
            favorite.note = note or favorite.note
        else:
            self.db.add(
                VideoFavorite(
                    user_id=user_id,
                    video_id=video_id,
                    note=note,
                    created_at=datetime.now(),
                )
            )
        self.db.commit()
        return True

    def remove_from_favorites(self, user_id: int, video_id: int) -> bool:
        favorite = (
            self.db.query(VideoFavorite)
            .filter(and_(VideoFavorite.user_id == user_id, VideoFavorite.video_id == video_id))
            .first()
        )
        if not favorite:
            return False
        self.db.delete(favorite)
        self.db.commit()
        return True

    def get_favorites(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        query = (
            self.db.query(Video)
            .join(VideoFavorite, Video.id == VideoFavorite.video_id)
            .filter(VideoFavorite.user_id == user_id, Video.is_active == 1)
            .order_by(VideoFavorite.created_at.desc())
        )
        total = query.count()
        videos = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_video(video) for video in videos],
        }

    @staticmethod
    def _serialize_video(video: Video) -> Dict[str, Any]:
        return {
            "id": video.id,
            "title": video.title,
            "url": video.url,
            "source": video.source,
            "duration": video.duration,
            "author": video.author,
            "view_count": video.view_count,
            "subject_id": video.subject_id,
            "chapter_id": video.chapter_id,
            "thumbnail": video.thumbnail,
            "description": video.description,
            "tags": video.tags or [],
        }
