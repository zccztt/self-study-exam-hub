# -*- coding: utf-8 -*-
"""Video resource service."""

import html
import base64
import binascii
import re
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.models.favorite import VideoFavorite
from backend.models.question import Question
from backend.models.subject import Subject
from backend.models.chapter import Chapter, KnowledgePoint
from backend.models.video import Video, VideoKnowledgePoint, VideoQuestion, VideoSource


class VideoService:
    BILIBILI_SEARCH_URL = "https://api.bilibili.com/x/web-interface/search/type"
    BING_SEARCH_URL = "https://www.bing.com/search"
    SO_SEARCH_URL = "https://www.so.com/s"
    USER_AGENT = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125 Safari/537.36"
    )
    INVALID_VIDEO_PATTERNS = [
        "example.com",
        "placeholder",
        "占位",
        "search.bilibili.com",
        "/all?keyword=",
        "zikao.neea.edu.cn",
        "www.neea.edu.cn",
        "官方入口",
        "检索入口",
        "B站检索",
    ]

    ONLINE_VIDEO_SOURCES = (
        VideoSource.BILIBILI.value,
        VideoSource.NETEASE.value,
        VideoSource.TENCENT.value,
        VideoSource.YOUTUBE.value,
    )
    VIDEO_SOURCE_VALUES = tuple(source.value for source in VideoSource)
    SOURCE_LABELS = {
        VideoSource.BILIBILI.value: "B站",
        VideoSource.NETEASE.value: "网易公开课",
        VideoSource.TENCENT.value: "腾讯课堂",
        VideoSource.YOUTUBE.value: "YouTube",
        VideoSource.CUSTOM.value: "公开视频",
    }

    def __init__(self, db: Session):
        self.db = db

    def search_videos(
        self,
        keyword: Optional[str] = None,
        subject_id: Optional[int] = None,
        chapter_ids: Optional[List[int]] = None,
        source: Optional[str] = None,
        online_search: bool = False,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        self._deactivate_invalid_videos()
        query = self._build_search_query(keyword, subject_id, chapter_ids, source)

        total = query.count()
        online_saved_count = 0
        if total == 0 and page == 1 and online_search:
            online_saved_count = self._search_and_save_online_videos(
                keyword=keyword,
                subject_id=subject_id,
                chapter_ids=chapter_ids,
                source=source,
                limit=max(8, min(page_size, 20)),
            )
            if online_saved_count:
                query = self._build_search_query(keyword, subject_id, chapter_ids, source)
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
            "online_saved_count": online_saved_count,
            "online_searched": online_search and (total == 0 or online_saved_count > 0),
            "message": (
                f"本地无匹配视频，已线上搜索并保存 {online_saved_count} 个真实视频链接。"
                if online_saved_count
                else None
            ),
            "items": [self._serialize_video(video) for video in videos],
        }

    def get_video_detail(self, video_id: int) -> Optional[Dict[str, Any]]:
        self._deactivate_invalid_videos()
        video = self.db.query(Video).filter(Video.id == video_id, Video.is_active == 1).first()
        if not video:
            return None
        data = self._serialize_video(video)
        data["related_questions"] = self.get_related_questions(video_id)
        data["knowledge_points"] = self.get_video_knowledge_points(video_id)
        return data

    def get_video_knowledge_points(self, video_id: int) -> List[Dict[str, Any]]:
        points = (
            self.db.query(KnowledgePoint, Chapter.name.label("chapter_name"))
            .join(VideoKnowledgePoint, KnowledgePoint.id == VideoKnowledgePoint.knowledge_point_id)
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .filter(VideoKnowledgePoint.video_id == video_id)
            .order_by(KnowledgePoint.frequency.desc(), KnowledgePoint.id.asc())
            .all()
        )
        return [
            {
                "id": point.id,
                "name": point.name,
                "chapter_id": point.chapter_id,
                "chapter_name": chapter_name,
                "importance": point.importance,
                "frequency": point.frequency,
            }
            for point, chapter_name in points
        ]

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
        valid = VideoService._is_real_video_url(video_url)
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
        self._deactivate_invalid_videos()
        query = (
            self.db.query(Video, VideoFavorite.note)
            .join(VideoFavorite, Video.id == VideoFavorite.video_id)
            .filter(VideoFavorite.user_id == user_id, Video.is_active == 1)
            .order_by(VideoFavorite.created_at.desc())
        )
        total = query.count()
        rows = query.offset((page - 1) * page_size).limit(page_size).all()
        items = []
        for video, favorite_note in rows:
            item = self._serialize_video(video)
            item["favorite_note"] = favorite_note
            items.append(item)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": items,
        }

    def _build_search_query(
        self,
        keyword: Optional[str],
        subject_id: Optional[int],
        chapter_ids: Optional[List[int]],
        source: Optional[str],
    ):
        query = self.db.query(Video).filter(Video.is_active == 1)
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(or_(Video.title.ilike(pattern), Video.description.ilike(pattern), Video.tags.ilike(pattern)))
        if subject_id:
            query = query.filter(Video.subject_id == subject_id)
        if chapter_ids:
            query = query.filter(Video.chapter_id.in_(chapter_ids))
        if source:
            query = query.filter(Video.source == source)
        return query

    def _deactivate_invalid_videos(self) -> int:
        rows = self.db.query(Video).filter(Video.is_active == 1).all()
        changed = 0
        for video in rows:
            if self._is_invalid_video_record(video):
                video.is_active = 0
                changed += 1
        if changed:
            self.db.commit()
        return changed

    def _search_and_save_online_videos(
        self,
        *,
        keyword: Optional[str],
        subject_id: Optional[int],
        chapter_ids: Optional[List[int]],
        source: Optional[str],
        limit: int,
    ) -> int:
        subject = self._resolve_video_subject(subject_id)
        if not subject:
            return 0

        chapter = self._resolve_video_chapter(chapter_ids)
        search_keyword = self._build_video_search_keyword(keyword, subject, chapter)
        sources = self._online_sources_for_request(source)
        if not sources:
            return 0

        search_limit = max(1, limit)
        per_source_limit = (
            search_limit
            if len(sources) == 1
            else max(2, min(search_limit, (search_limit + len(sources) - 1) // len(sources)))
        )
        online_items: List[Dict[str, Any]] = []
        for platform_source in sources:
            online_items.extend(
                self._search_platform_videos(
                    platform_source,
                    search_keyword,
                    limit=per_source_limit,
                )
            )

        saved_count = 0
        for item in self._dedupe_video_items(online_items):
            if saved_count >= search_limit:
                break
            if self._save_online_video(item, subject.id, chapter.id if chapter else None, search_keyword):
                saved_count += 1
        if saved_count:
            self.db.commit()
        return saved_count

    @classmethod
    def _online_sources_for_request(cls, source: Optional[str]) -> List[str]:
        if not source:
            return list(cls.ONLINE_VIDEO_SOURCES)
        source_value = str(source).strip()
        return [source_value] if source_value in cls.ONLINE_VIDEO_SOURCES else []

    def _resolve_video_subject(self, subject_id: Optional[int]) -> Optional[Subject]:
        if subject_id:
            return self.db.query(Subject).filter(Subject.id == subject_id).first()
        return self.db.query(Subject).order_by(Subject.code.asc(), Subject.id.asc()).first()

    def _resolve_video_chapter(self, chapter_ids: Optional[List[int]]) -> Optional[Chapter]:
        if not chapter_ids:
            return None
        return self.db.query(Chapter).filter(Chapter.id == chapter_ids[0]).first()

    @staticmethod
    def _build_video_search_keyword(keyword: Optional[str], subject: Subject, chapter: Optional[Chapter]) -> str:
        parts = [
            "自考",
            str(datetime.now().year),
            subject.code,
            subject.name,
            chapter.name if chapter else "",
            keyword or "",
            "精讲 真题 解析",
        ]
        return " ".join(part.strip() for part in parts if str(part or "").strip())

    def _search_platform_videos(self, source: str, keyword: str, limit: int) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        if source == VideoSource.BILIBILI.value:
            return self._search_bilibili_videos(keyword, limit)
        if source == VideoSource.NETEASE.value:
            return self._search_netease_videos(keyword, limit)
        if source == VideoSource.TENCENT.value:
            return self._search_tencent_videos(keyword, limit)
        if source == VideoSource.YOUTUBE.value:
            return self._search_youtube_videos(keyword, limit)
        return []

    def _search_bilibili_videos(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        videos: List[Dict[str, Any]] = []
        try:
            response = httpx.get(
                self.BILIBILI_SEARCH_URL,
                params={
                    "search_type": "video",
                    "keyword": keyword,
                    "page": 1,
                    "page_size": min(max(limit, 1), 20),
                },
                headers={"User-Agent": self.USER_AGENT, "Referer": "https://www.bilibili.com/"},
                timeout=10,
                follow_redirects=True,
            )
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError):
            payload = {}

        if payload.get("code") == 0:
            for item in payload.get("data", {}).get("result") or []:
                normalized = self._normalize_bilibili_item(item)
                if normalized:
                    videos.append(normalized)
                if len(videos) >= limit:
                    break
        if videos:
            return videos
        videos.extend(self._search_bing_video_pages(keyword, limit=limit, source=VideoSource.BILIBILI.value))
        if len(videos) < limit:
            videos.extend(
                self._search_so_video_pages(
                    keyword,
                    limit=limit - len(videos),
                    source=VideoSource.BILIBILI.value,
                )
            )
        return self._dedupe_video_items(videos)[:limit]

    def _search_netease_videos(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        queries = [
            f"{keyword} site:open.163.com/newview/movie",
            f"{keyword} site:study.163.com/course",
            f"{keyword} site:icourse163.org/course",
            f"{keyword} 网易公开课 视频",
        ]
        return self._search_generic_platform_pages(VideoSource.NETEASE.value, keyword, queries, limit)

    def _search_tencent_videos(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        queries = [
            f"{keyword} site:v.qq.com/x/page",
            f"{keyword} site:v.qq.com/x/cover",
            f"{keyword} site:ke.qq.com/course",
            f"{keyword} 腾讯课堂 腾讯视频",
        ]
        return self._search_generic_platform_pages(VideoSource.TENCENT.value, keyword, queries, limit)

    def _search_youtube_videos(self, keyword: str, limit: int) -> List[Dict[str, Any]]:
        queries = [
            f"{keyword} site:youtube.com/watch",
            f"{keyword} site:youtu.be",
            f"{keyword} YouTube 自考",
        ]
        return self._search_generic_platform_pages(VideoSource.YOUTUBE.value, keyword, queries, limit)

    def _search_generic_platform_pages(
        self,
        source: str,
        keyword: str,
        queries: List[str],
        limit: int,
    ) -> List[Dict[str, Any]]:
        videos = self._search_bing_video_pages(keyword, limit=limit, source=source, queries=queries)
        if len(videos) < limit:
            videos.extend(
                self._search_so_video_pages(
                    keyword,
                    limit=limit - len(videos),
                    source=source,
                    queries=queries[:2],
                )
            )
        return self._dedupe_video_items(videos)[:limit]

    def _search_bing_video_pages(
        self,
        keyword: str,
        limit: int,
        source: str = VideoSource.BILIBILI.value,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        search_queries = queries or [
            f"{keyword} bilibili BV",
            f"{keyword} site:bilibili.com/video",
            f"{keyword} B站 视频",
        ]
        videos: List[Dict[str, Any]] = []
        for query in search_queries:
            try:
                response = httpx.get(
                    self.BING_SEARCH_URL,
                    params={"q": query, "format": "rss", "mkt": "zh-CN", "setlang": "zh-CN"},
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=10,
                    follow_redirects=True,
                )
                response.raise_for_status()
                root = ET.fromstring(response.text)
            except (httpx.HTTPError, ET.ParseError):
                continue

            for item in root.findall(".//item"):
                title = self._clean_text(item.findtext("title"))
                link = self._clean_url(item.findtext("link"))
                description = self._clean_text(item.findtext("description"))
                normalized = self._normalize_platform_search_video_result(title, link, description, source)
                if normalized:
                    videos.append(normalized)
                if len(videos) >= limit:
                    return self._dedupe_video_items(videos)
        return self._dedupe_video_items(videos)

    def _search_so_video_pages(
        self,
        keyword: str,
        limit: int,
        source: str = VideoSource.BILIBILI.value,
        queries: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        search_queries = queries or [f"{keyword} bilibili BV"]
        videos: List[Dict[str, Any]] = []
        for query in search_queries:
            try:
                response = httpx.get(
                    self.SO_SEARCH_URL,
                    params={"q": query},
                    headers={"User-Agent": self.USER_AGENT},
                    timeout=10,
                    follow_redirects=True,
                )
                response.raise_for_status()
            except httpx.HTTPError:
                continue

            for block in re.findall(r"<li[^>]*>.*?</li>", response.text, re.S):
                title_match = re.search(r"<h3[^>]*>.*?</h3>", block, re.S)
                link_match = re.search(r'href="([^"]+)"', block)
                title = self._clean_text(title_match.group(0) if title_match else "")
                link = self._clean_url(link_match.group(1) if link_match else "")
                description = self._clean_text(block)
                normalized = self._normalize_platform_search_video_result(title, link, description, source)
                if normalized:
                    videos.append(normalized)
                if len(videos) >= limit:
                    return self._dedupe_video_items(videos)
        return self._dedupe_video_items(videos)

    @classmethod
    def _normalize_search_video_result(cls, title: str, link: str, description: str) -> Optional[Dict[str, Any]]:
        return cls._normalize_platform_search_video_result(title, link, description, VideoSource.BILIBILI.value)

    @classmethod
    def _normalize_platform_search_video_result(
        cls,
        title: str,
        link: str,
        description: str,
        source: str,
    ) -> Optional[Dict[str, Any]]:
        url = cls._canonical_platform_video_url(source, link, description)
        if not url or not cls._is_real_video_url(url):
            return None
        source_label = cls.SOURCE_LABELS.get(source, source)
        clean_title = title or description[:80] or f"{source_label}课程视频"
        return {
            "title": clean_title[:300],
            "url": url,
            "duration": None,
            "author": "线上实时搜索",
            "view_count": 0,
            "publish_date": None,
            "thumbnail": None,
            "source": source,
        }

    @classmethod
    def _canonical_platform_video_url(cls, source: str, link: str, description: str = "") -> Optional[str]:
        if source == VideoSource.BILIBILI.value:
            bvid = cls._extract_bvid(f"{link} {description}")
            return f"https://www.bilibili.com/video/{bvid}" if bvid else None

        for candidate in cls._candidate_video_urls(link, description):
            normalized = cls._canonicalize_candidate_url(source, candidate)
            if normalized:
                return normalized
        return None

    @classmethod
    def _candidate_video_urls(cls, *values: Any) -> List[str]:
        candidates: List[str] = []
        for value in values:
            raw_text = str(value or "").strip()
            if not raw_text:
                continue
            text_variants = {
                raw_text,
                html.unescape(raw_text),
                urllib.parse.unquote(html.unescape(raw_text)),
            }
            for text in text_variants:
                direct = cls._clean_url(text).strip().rstrip(").,;，。")
                if direct.startswith(("http://", "https://")):
                    candidates.append(direct)
                for match in re.findall(r"https?://[^\s\"'<>]+", text):
                    url = cls._clean_url(match).strip().rstrip(").,;，。")
                    if url.startswith(("http://", "https://")):
                        candidates.append(url)
        return cls._dedupe_urls(candidates)

    @staticmethod
    def _dedupe_urls(urls: List[str]) -> List[str]:
        seen = set()
        deduped: List[str] = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            deduped.append(url)
        return deduped

    @classmethod
    def _canonicalize_candidate_url(cls, source: str, candidate: str) -> Optional[str]:
        url = cls._clean_url(candidate)
        parsed = urllib.parse.urlparse(url)
        host = parsed.netloc.lower()
        path = parsed.path
        scheme = parsed.scheme or "https"

        if source == VideoSource.YOUTUBE.value:
            video_id = cls._extract_youtube_video_id(parsed)
            if video_id:
                return f"https://www.youtube.com/watch?v={video_id}"
            return None

        if source == VideoSource.TENCENT.value:
            if host.endswith("v.qq.com") and path.startswith("/x/"):
                return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", "", ""))
            if host.endswith("ke.qq.com") and path.startswith("/course/"):
                return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", "", ""))
            return None

        if source == VideoSource.NETEASE.value:
            if host.endswith("open.163.com") and path.startswith("/newview/movie"):
                return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", parsed.query, ""))
            if host.endswith("study.163.com") and path.startswith("/course"):
                return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", parsed.query, ""))
            if host.endswith("icourse163.org") and (path.startswith("/course") or path.startswith("/learn")):
                return urllib.parse.urlunparse((scheme, parsed.netloc, path, "", parsed.query, ""))
            return None

        return None

    @staticmethod
    def _extract_youtube_video_id(parsed: urllib.parse.ParseResult) -> Optional[str]:
        host = parsed.netloc.lower()
        path_parts = [part for part in parsed.path.split("/") if part]
        video_id = None
        if host.endswith("youtu.be") and path_parts:
            video_id = path_parts[0]
        elif host.endswith("youtube.com") or host.endswith("youtube-nocookie.com"):
            if parsed.path == "/watch":
                video_id = (urllib.parse.parse_qs(parsed.query).get("v") or [None])[0]
            elif len(path_parts) >= 2 and path_parts[0] in {"embed", "shorts"}:
                video_id = path_parts[1]
        if video_id and re.match(r"^[0-9A-Za-z_-]{6,32}$", video_id):
            return video_id
        return None

    @staticmethod
    def _dedupe_video_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        seen = set()
        deduped: List[Dict[str, Any]] = []
        for item in items:
            url = item.get("url")
            if not url or url in seen:
                continue
            seen.add(url)
            deduped.append(item)
        return deduped

    def _save_online_video(
        self,
        item: Dict[str, Any],
        subject_id: int,
        chapter_id: Optional[int],
        search_keyword: str,
    ) -> bool:
        url = str(item.get("url") or "").strip()
        if not self._is_real_video_url(url):
            return False
        source = self._normalize_video_source(item.get("source"))
        source_label = self.SOURCE_LABELS.get(source, source)
        existing = self.db.query(Video).filter(Video.url == url).first()
        if existing:
            changed = existing.is_active != 1
            existing.is_active = 1
            existing.subject_id = existing.subject_id or subject_id
            existing.chapter_id = existing.chapter_id or chapter_id
            existing.source = existing.source or source
            existing.view_count = max(existing.view_count or 0, int(item.get("view_count") or 0))
            existing.thumbnail = existing.thumbnail or item.get("thumbnail")
            existing.tags = list(dict.fromkeys([*(existing.tags or []), "线上补充", "真实视频", source_label]))
            return changed

        video = Video(
            title=str(item.get("title") or url)[:300],
            url=url,
            source=source,
            duration=item.get("duration"),
            author=str(item.get("author") or "")[:100] or None,
            view_count=int(item.get("view_count") or 0),
            publish_date=item.get("publish_date"),
            subject_id=subject_id,
            chapter_id=chapter_id,
            thumbnail=item.get("thumbnail"),
            description=f"线上实时搜索并保存的公开学习视频资源。来源：{source_label}；检索词：{search_keyword}",
            tags=["线上补充", "真实视频", source_label, f"{datetime.now().year}备考"],
            is_active=1,
        )
        self.db.add(video)
        return True

    @classmethod
    def _normalize_video_source(cls, source: Any) -> str:
        source_value = str(source or "").strip()
        if source_value in cls.VIDEO_SOURCE_VALUES:
            return source_value
        return VideoSource.BILIBILI.value

    @classmethod
    def _normalize_bilibili_item(cls, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        title = cls._clean_text(item.get("title"))
        bvid = item.get("bvid") or cls._extract_bvid(str(item.get("arcurl") or item.get("url") or ""))
        if not title or not bvid:
            return None
        return {
            "title": title[:300],
            "url": f"https://www.bilibili.com/video/{bvid}",
            "duration": cls._parse_duration(item.get("duration")),
            "author": cls._clean_text(item.get("author") or item.get("mid"))[:100],
            "view_count": cls._parse_count(item.get("play")),
            "publish_date": cls._parse_publish_date(item.get("pubdate") or item.get("senddate")),
            "thumbnail": cls._normalize_image_url(item.get("pic")),
            "source": VideoSource.BILIBILI.value,
        }

    @classmethod
    def _is_invalid_video_record(cls, video: Video) -> bool:
        combined = " ".join(
            str(value or "")
            for value in [video.url, video.title, video.description, " ".join(video.tags or [])]
        )
        if any(pattern.lower() in combined.lower() for pattern in cls.INVALID_VIDEO_PATTERNS):
            return True
        return not cls._is_real_video_url(video.url)

    @staticmethod
    def _is_real_video_url(video_url: str) -> bool:
        url = str(video_url or "").strip().lower()
        if not url.startswith(("http://", "https://")):
            return False
        if "bilibili.com/video/bv" in url:
            return True
        if "youtu.be/" in url or "youtube.com/watch" in url or "youtube.com/shorts/" in url:
            return True
        if "v.qq.com/x/" in url or "ke.qq.com/course/" in url:
            return True
        if (
            "open.163.com/newview/movie" in url
            or "study.163.com/course" in url
            or "icourse163.org/course" in url
            or "icourse163.org/learn" in url
        ):
            return True
        return False

    @staticmethod
    def _extract_bvid(value: str) -> Optional[str]:
        match = re.search(r"(BV[0-9A-Za-z]{10})", value)
        return match.group(1) if match else None

    @staticmethod
    def _clean_text(value: Any) -> str:
        text = html.unescape(str(value or ""))
        text = re.sub(r"<[^>]+>", "", text)
        return re.sub(r"\s+", " ", text).strip()

    @classmethod
    def _clean_url(cls, value: Any) -> str:
        url = html.unescape(str(value or "")).strip()
        if not url:
            return ""
        if url.startswith("//"):
            url = f"https:{url}"

        parsed = urllib.parse.urlparse(url)
        if not parsed.scheme and not parsed.netloc:
            return url

        query = urllib.parse.parse_qs(parsed.query)
        if "bing.com" in parsed.netloc and parsed.path.startswith("/ck/"):
            decoded = cls._decode_redirect_target(query)
            if decoded:
                return decoded
        if parsed.netloc.endswith("so.com") or parsed.netloc.endswith("360.cn"):
            decoded = cls._decode_redirect_target(query)
            if decoded:
                return decoded
        return url

    @staticmethod
    def _decode_redirect_target(query: Dict[str, List[str]]) -> str:
        for key in ("url", "u", "r", "target"):
            for raw_value in query.get(key, []):
                value = urllib.parse.unquote(raw_value).strip()
                if value.startswith(("http://", "https://")):
                    return value
                encoded = value[2:] if value.startswith("a1") else value
                padding = "=" * (-len(encoded) % 4)
                try:
                    decoded = base64.urlsafe_b64decode(f"{encoded}{padding}").decode("utf-8", errors="ignore")
                except (binascii.Error, ValueError, TypeError):
                    continue
                if decoded.startswith(("http://", "https://")):
                    return decoded
        return ""

    @staticmethod
    def _parse_count(value: Any) -> int:
        if isinstance(value, int):
            return value
        text = str(value or "").replace(",", "").strip()
        if not text or text == "--":
            return 0
        multiplier = 1
        if text.endswith("万"):
            multiplier = 10000
            text = text[:-1]
        elif text.endswith("亿"):
            multiplier = 100000000
            text = text[:-1]
        try:
            return int(float(text) * multiplier)
        except ValueError:
            return 0

    @staticmethod
    def _parse_duration(value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value
        text = str(value or "").strip()
        if text.isdigit():
            return int(text)
        parts = [int(part) for part in text.split(":") if part.isdigit()]
        if len(parts) == 3:
            return parts[0] * 3600 + parts[1] * 60 + parts[2]
        if len(parts) == 2:
            return parts[0] * 60 + parts[1]
        return None

    @staticmethod
    def _parse_publish_date(value: Any) -> Optional[datetime]:
        try:
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        except (TypeError, ValueError, OSError):
            return None

    @staticmethod
    def _normalize_image_url(value: Any) -> Optional[str]:
        url = str(value or "").strip()
        if not url:
            return None
        if url.startswith("//"):
            return f"https:{url}"
        return url

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
