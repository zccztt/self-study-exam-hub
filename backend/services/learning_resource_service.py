# -*- coding: utf-8 -*-
"""Legal public learning-resource discovery by self-study course code."""

from __future__ import annotations

from typing import Any, Dict, List
from urllib.parse import urlparse

from backend.config import settings
from backend.models.subject import Subject


VERIFIED_RESOURCES: Dict[str, List[Dict[str, Any]]] = {
    "15043": [
        {
            "title": "《中国近现代史纲要（2023年版）》正版教材信息",
            "url": "https://xuanshu.hep.com.cn/front/h5Mobile/bookDetails?bookId=65564c2374ce561611bd9883",
            "resource_type": "textbook_info",
            "source": "高等教育出版社",
            "access_note": "可免费查看正版教材信息；不是免费全文电子书。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "中国近现代史纲要公开课程",
            "url": "https://higher.smartedu.cn/course/68ac494ad5f9b8b6cf61fae3",
            "resource_type": "open_course",
            "source": "国家高等教育智慧教育平台",
            "access_note": "国家平台公开课程，按平台规则免费学习。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "《15043 中国近现代史纲要》课程考试大纲",
            "url": "https://www.jseea.cn/webfile/selflearning_jcdg/2025-02-25/7300038163492245504.html",
            "resource_type": "exam_outline",
            "source": "江苏省教育考试院",
            "access_note": "官方公开考试大纲，可直接在线查看。",
            "is_free": True,
            "is_full_text": True,
            "verified": True,
        },
        {
            "title": "中国近现代史纲要（浙江大学）",
            "url": "https://www.icourse163.org/learn/ZJU-21001?tid=1472202446",
            "resource_type": "open_course",
            "source": "中国大学 MOOC",
            "access_note": "公开在线课程，具体开放周期以平台为准。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "百分自考网：15043 中国近现代史纲要资料入口",
            "url": "https://www.exam100.net/index.php?m=exam&c=index&a=lists&catid=19",
            "resource_type": "study_materials",
            "source": "百分自考网",
            "access_note": "可查看课程真题和练习资料；未证明存在授权的整本免费电子教材，下载前请核对版权和版本。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "自考生网：15043/03708 课程资料入口",
            "url": "https://www.zikaosw.cn/zkkm/9.html",
            "resource_type": "study_materials",
            "source": "自考生网",
            "access_note": "包含真题、题库、考试大纲、教材购买和网课试听入口；教材全文是否免费及授权状态需以具体页面为准。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "自考365：教材与考试大纲目录",
            "url": "https://www.zikao365.com/jcdg",
            "resource_type": "catalog",
            "source": "自考365",
            "access_note": "用于按课程代码核对教材版本和考试大纲，不是电子教材全文页面。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
    ],
    "15044": [
        {
            "title": "《马克思主义基本原理（2023年版）》正版教材信息",
            "url": "https://xuanshu.hep.com.cn/front/book/findBookDetails?bookId=65564e7f74ce561611bd988f",
            "resource_type": "textbook_info",
            "source": "高等教育出版社",
            "access_note": "可免费查看正版教材信息；不是免费全文电子书。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "马克思主义基本原理公开课程",
            "url": "https://higher.smartedu.cn/course/68d1c127a9f4619f8f57675e",
            "resource_type": "open_course",
            "source": "国家高等教育智慧教育平台",
            "access_note": "国家平台公开课程，按平台规则免费学习。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "15044 马克思主义基本原理课程考试大纲",
            "url": "https://cjc.yctu.edu.cn/2025/0225/c8759a132100/page.htm",
            "resource_type": "exam_outline",
            "source": "盐城师范学院继续教育学院",
            "access_note": "学校公开发布的自学考试课程大纲。",
            "is_free": True,
            "is_full_text": True,
            "verified": True,
        },
        {
            "title": "马克思主义基本原理（武汉大学）",
            "url": "https://www.icourse163.org/course/whu-1001717003",
            "resource_type": "open_course",
            "source": "中国大学 MOOC",
            "access_note": "公开在线课程，具体开放周期以平台为准。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "百分自考网：15044 马克思主义基本原理资料入口",
            "url": "https://www.exam100.net/index.php?m=exam&c=index&a=lists&catid=20",
            "resource_type": "study_materials",
            "source": "百分自考网",
            "access_note": "可查看课程真题和模拟资料；未证明存在授权的整本免费电子教材，下载前请核对版权和版本。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "自考生网：15044/03709 课程资料入口",
            "url": "https://www.zikaosw.cn/zkkm/702.html",
            "resource_type": "study_materials",
            "source": "自考生网",
            "access_note": "可进入真题、题库、教材和网课相关资料；教材全文是否免费及授权状态需以具体页面为准。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
        {
            "title": "自考365：教材与考试大纲目录",
            "url": "https://www.zikao365.com/jcdg",
            "resource_type": "catalog",
            "source": "自考365",
            "access_note": "用于按课程代码核对教材版本和考试大纲，不是电子教材全文页面。",
            "is_free": True,
            "is_full_text": False,
            "verified": True,
        },
    ],
}


class LearningResourceService:
    """Return curated resources and optionally discover additional official links."""

    ALLOWED_HOST_SUFFIXES = (
        ".gov.cn", ".edu.cn", "neea.edu.cn", "smartedu.cn",
        "hep.com.cn", "icourse163.org", "bilibili.com",
        "exam100.net", "zikaosw.cn", "zikao365.com",
    )

    def list_resources(self, subject: Subject, online_search: bool = False, limit: int = 10) -> Dict[str, Any]:
        resources = [dict(item) for item in VERIFIED_RESOURCES.get(subject.code, [])]
        if online_search:
            resources.extend(self._discover(subject, limit=limit))
        unique: List[Dict[str, Any]] = []
        seen = set()
        for item in resources:
            url = str(item.get("url") or "").strip()
            if not url or url in seen:
                continue
            seen.add(url)
            unique.append(item)
            if len(unique) >= limit:
                break
        has_full_text = any(
            item.get("is_full_text") and item.get("resource_type") == "textbook"
            for item in unique
        )
        return {
            "subject_id": subject.id,
            "subject_code": subject.code,
            "subject_name": subject.name,
            "items": unique,
            "has_authorized_full_text_textbook": has_full_text,
            "online_searched": online_search,
            "notice": (
                "未发现可确认授权的整本免费电子教材；以下展示正版教材信息、官方考试大纲、公开课程和第三方资料入口。"
                if not has_full_text else "已发现明确标注为开放访问的教材全文。"
            ),
        }

    def _discover(self, subject: Subject, limit: int) -> List[Dict[str, Any]]:
        if not settings.TAVILY_API_KEY or not settings.TAVILY_API_URL:
            return []
        try:
            from tavily import TavilyClient  # type: ignore[import-untyped]
            client = TavilyClient(
                api_key=settings.TAVILY_API_KEY,
                api_base_url=settings.TAVILY_API_URL.rstrip("/"),
            )
            response = client.search(
                query=f"{subject.code} {subject.name} 自学考试 官方 考试大纲 公开课程 教材信息",
                search_depth="basic",
                max_results=max(limit, 6),
                include_domains=[
                    "gov.cn", "edu.cn", "neea.edu.cn", "smartedu.cn",
                    "hep.com.cn", "icourse163.org", "bilibili.com",
                    "exam100.net", "zikaosw.cn", "zikao365.com",
                ],
            )
        except Exception:
            return []
        items: List[Dict[str, Any]] = []
        for result in response.get("results", []) if isinstance(response, dict) else []:
            title = str(result.get("title") or "").strip()
            url = str(result.get("url") or "").strip()
            if not title or not self._is_allowed_url(url):
                continue
            resource_type = self._classify(title, url)
            if not resource_type:
                continue
            items.append({
                "title": title,
                "url": url,
                "resource_type": resource_type,
                "source": urlparse(url).hostname or "公开资源",
                "access_note": self._access_note(resource_type),
                "is_free": True,
                "is_full_text": resource_type == "exam_outline",
                "verified": False,
            })
        return items

    def _is_allowed_url(self, url: str) -> bool:
        hostname = (urlparse(url).hostname or "").lower()
        return bool(hostname) and any(
            hostname == suffix.lstrip(".") or hostname.endswith(suffix)
            for suffix in self.ALLOWED_HOST_SUFFIXES
        )

    @staticmethod
    def _classify(title: str, url: str) -> str:
        text = f"{title} {url}".lower()
        if any(token in text for token in ("考试大纲", "课程大纲", "教学大纲")):
            return "exam_outline"
        if any(token in text for token in ("公开课", "课程", "mooc", "慕课", "视频")):
            return "open_course"
        if any(token in text for token in ("教材信息", "图书", "bookdetails", "findbookdetails")):
            return "textbook_info"
        if any(token in text for token in ("资料", "真题", "题库", "网课", "教材目录", "考试大纲")):
            return "study_materials"
        return ""

    @staticmethod
    def _access_note(resource_type: str) -> str:
        return {
            "exam_outline": "公开考试或课程大纲，请以最新官方版本为准。",
            "open_course": "公开课程，开放周期和登录要求以来源平台为准。",
            "textbook_info": "正版教材信息页，不代表教材全文免费开放。",
            "study_materials": "第三方课程资料入口，需自行核对版权、版本和下载内容。",
            "catalog": "课程教材目录或资料导航，不是电子教材全文。",
        }.get(resource_type, "公开学习资源，请核对来源和使用条款。")
