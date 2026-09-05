# -*- coding: utf-8 -*-
"""Tests for multi-platform video collection helpers."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.models import Base
from backend.models.chapter import Chapter, KnowledgePoint
from backend.models.subject import Subject
from backend.models.video import Video, VideoKnowledgePoint, VideoSource
from backend.services.video_service import VideoService


def _build_db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    db = Session()
    db.add(Subject(id=1, code="03709", name="马克思主义基本原理概论"))
    db.commit()
    return db


def test_platform_search_result_normalizes_real_video_urls() -> None:
    youtube = VideoService._normalize_platform_search_video_result(
        "YT lesson",
        "https://www.youtube.com/watch?v=aBcDeFg1234&list=ignored",
        "",
        VideoSource.YOUTUBE.value,
    )
    tencent = VideoService._normalize_platform_search_video_result(
        "Tencent lesson",
        "https://v.qq.com/x/page/m1234567890.html?ptag=search",
        "",
        VideoSource.TENCENT.value,
    )
    netease = VideoService._normalize_platform_search_video_result(
        "NetEase lesson",
        "https://open.163.com/newview/movie/free?pid=ABC123&mid=DEF456#fragment",
        "",
        VideoSource.NETEASE.value,
    )

    assert youtube is not None
    assert youtube["url"] == "https://www.youtube.com/watch?v=aBcDeFg1234"
    assert youtube["source"] == VideoSource.YOUTUBE.value
    assert tencent is not None
    assert tencent["url"] == "https://v.qq.com/x/page/m1234567890.html"
    assert tencent["source"] == VideoSource.TENCENT.value
    assert netease is not None
    assert netease["url"] == "https://open.163.com/newview/movie/free?pid=ABC123&mid=DEF456"
    assert netease["source"] == VideoSource.NETEASE.value


def test_save_online_video_preserves_platform_source() -> None:
    db = _build_db_session()
    try:
        service = VideoService(db)
        saved = service._save_online_video(
            {
                "title": "YouTube lesson",
                "url": "https://www.youtube.com/watch?v=aBcDeFg1234",
                "source": VideoSource.YOUTUBE.value,
                "author": "online search",
            },
            subject_id=1,
            chapter_id=None,
            search_keyword="自考 03709",
        )
        db.commit()

        video = db.query(Video).filter(Video.url == "https://www.youtube.com/watch?v=aBcDeFg1234").one()
        assert saved is True
        assert video.source == VideoSource.YOUTUBE.value
        assert "YouTube" in (video.tags or [])
    finally:
        db.close()


def test_video_favorite_returns_saved_note() -> None:
    db = _build_db_session()
    try:
        video = Video(
            title="复习视频",
            url="https://www.bilibili.com/video/BV1example",
            source=VideoSource.BILIBILI.value,
            subject_id=1,
            is_active=True,
        )
        db.add(video)
        db.commit()

        service = VideoService(db)
        assert service.add_to_favorites(1, video.id, "第二章考前复习") is True
        result = service.get_favorites(1)
        assert result["items"][0]["favorite_note"] == "第二章考前复习"
    finally:
        db.close()


def test_video_detail_returns_related_knowledge_points() -> None:
    db = _build_db_session()
    try:
        chapter = Chapter(id=1, subject_id=1, name="第一章", order=1)
        point = KnowledgePoint(id=1, chapter_id=1, name="实践与认识", frequency=4)
        video = Video(
            title="考点视频",
            url="https://www.bilibili.com/video/BV1example2",
            source=VideoSource.BILIBILI.value,
            subject_id=1,
            chapter_id=1,
            is_active=True,
        )
        db.add_all([chapter, point, video])
        db.commit()
        db.add(VideoKnowledgePoint(video_id=video.id, knowledge_point_id=point.id))
        db.commit()

        detail = VideoService(db).get_video_detail(video.id)

        assert detail is not None
        assert detail["knowledge_points"][0]["name"] == "实践与认识"
        assert detail["knowledge_points"][0]["chapter_name"] == "第一章"
    finally:
        db.close()


def test_online_search_dispatches_selected_platform(monkeypatch) -> None:
    db = _build_db_session()
    try:
        service = VideoService(db)
        calls = []

        def fake_search(source: str, keyword: str, limit: int):
            calls.append((source, keyword, limit))
            return [
                {
                    "title": "Tencent lesson",
                    "url": "https://v.qq.com/x/page/m1234567890.html",
                    "source": source,
                }
            ]

        monkeypatch.setattr(service, "_search_platform_videos", fake_search)

        saved_count = service._search_and_save_online_videos(
            keyword="真题解析",
            subject_id=1,
            chapter_ids=None,
            source=VideoSource.TENCENT.value,
            limit=5,
        )

        video = db.query(Video).filter(Video.url == "https://v.qq.com/x/page/m1234567890.html").one()
        assert saved_count == 1
        assert calls and calls[0][0] == VideoSource.TENCENT.value
        assert calls[0][2] == 5
        assert video.source == VideoSource.TENCENT.value
    finally:
        db.close()
