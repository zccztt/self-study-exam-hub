# -*- coding: utf-8 -*-
"""Initialize database schema and maintain 2026 demo-ready data."""

from datetime import datetime
from typing import Iterable, Optional

from sqlalchemy import or_

from backend.data.self_exam_catalog import build_subject_seed_data
from backend.database import SessionLocal, engine
from backend.elasticsearch_client import QUESTION_INDEX, QUESTION_INDEX_MAPPING, es_client
from backend.models import Base
from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.question import Difficulty, Question, QuestionType
from backend.models.subject import Subject
from backend.models.user import User
from backend.models.video import Video, VideoQuestion, VideoSource
from backend.utils import hash_password

DEMO_USERNAME = "demo"
DEMO_PASSWORD = "demo123456"
DEMO_EMAIL = "demo@self-study-exam-hub.local"

BILIBILI_MARX_URL = "https://www.bilibili.com/video/BV1hW41167NW"
BILIBILI_HISTORY_URL = "https://www.bilibili.com/video/BV1t4411e7Q5"


def init_database() -> None:
    Base.metadata.create_all(bind=engine)


def init_elasticsearch() -> None:
    es_client.create_index(QUESTION_INDEX, QUESTION_INDEX_MAPPING)


def _find_subject(db, code: str, old_codes: Iterable[str], name: str) -> Optional[Subject]:
    codes = [code, *old_codes]
    return (
        db.query(Subject)
        .filter(or_(Subject.code.in_(codes), Subject.name == name))
        .order_by(Subject.id.asc())
        .first()
    )


def _ensure_demo_user(db) -> User:
    user = (
        db.query(User)
        .filter(or_(User.username == DEMO_USERNAME, User.email == DEMO_EMAIL))
        .first()
    )
    if not user:
        user = User(username=DEMO_USERNAME, email=DEMO_EMAIL)
        db.add(user)

    user.username = DEMO_USERNAME
    user.email = DEMO_EMAIL
    user.full_name = "2026 自考演示账号"
    user.hashed_password = hash_password(DEMO_PASSWORD)
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def _ensure_subject(db, data: dict) -> Subject:
    subject = _find_subject(db, data["code"], data.get("old_codes", []), data["name"])
    if not subject:
        subject = Subject(code=data["code"], name=data["name"])
        db.add(subject)

    subject.code = data["code"]
    subject.name = data["name"]
    subject.category = data["category"]
    subject.description = data["description"]
    subject.exam_duration = data["exam_duration"]
    subject.total_score = data["total_score"]
    db.commit()
    db.refresh(subject)
    return subject


def _ensure_chapter(db, subject_id: int, data: dict) -> Chapter:
    chapter = (
        db.query(Chapter)
        .filter(
            Chapter.subject_id == subject_id,
            or_(Chapter.order == data["order"], Chapter.name == data["name"]),
        )
        .order_by(Chapter.id.asc())
        .first()
    )
    if not chapter:
        chapter = Chapter(subject_id=subject_id, order=data["order"], name=data["name"])
        db.add(chapter)

    chapter.name = data["name"]
    chapter.order = data["order"]
    chapter.description = data.get("description")
    db.commit()
    db.refresh(chapter)
    return chapter


def _ensure_point(db, chapter_id: int, data: dict) -> KnowledgePoint:
    point = (
        db.query(KnowledgePoint)
        .filter(KnowledgePoint.chapter_id == chapter_id, KnowledgePoint.name == data["name"])
        .first()
    )
    if not point:
        point = KnowledgePoint(chapter_id=chapter_id, name=data["name"])
        db.add(point)

    point.description = data["description"]
    point.importance = data["importance"]
    point.frequency = data["frequency"]
    db.commit()
    db.refresh(point)
    return point


def _ensure_question(db, subject_id: int, chapter_id: int, data: dict) -> Question:
    question = (
        db.query(Question)
        .filter(Question.subject_id == subject_id, Question.content == data["content"])
        .first()
    )
    if not question:
        question = Question(subject_id=subject_id, chapter_id=chapter_id, content=data["content"])
        db.add(question)

    question.question_type = data["question_type"]
    question.options = data.get("options", [])
    question.answer = data["answer"]
    question.explanation = data["explanation"]
    question.year = 2026
    question.month = data.get("month", 4)
    question.difficulty = data["difficulty"]
    question.frequency = data["frequency"]
    question.score = data["score"]
    question.source = data["source"]
    db.commit()
    db.refresh(question)
    return question


def _ensure_question_point(db, question_id: int, point_id: int) -> None:
    exists = (
        db.query(QuestionKnowledgePoint)
        .filter(
            QuestionKnowledgePoint.question_id == question_id,
            QuestionKnowledgePoint.knowledge_point_id == point_id,
        )
        .first()
    )
    if not exists:
        db.add(QuestionKnowledgePoint(question_id=question_id, knowledge_point_id=point_id))
        db.commit()


def _ensure_video(db, subject_id: int, chapter_id: Optional[int], data: dict) -> Video:
    video = db.query(Video).filter(Video.url == data["url"]).first()
    if not video:
        video = Video(url=data["url"])
        db.add(video)

    video.title = data["title"]
    video.source = data["source"]
    video.duration = data.get("duration")
    video.author = data.get("author")
    video.view_count = data.get("view_count", 0)
    video.publish_date = data.get("publish_date")
    video.subject_id = subject_id
    video.chapter_id = chapter_id
    video.thumbnail = data.get("thumbnail")
    video.description = data["description"]
    video.tags = data.get("tags", [])
    video.is_active = 1
    db.commit()
    db.refresh(video)
    return video


def _ensure_video_question(db, video_id: int, question_id: int) -> None:
    exists = (
        db.query(VideoQuestion)
        .filter(VideoQuestion.video_id == video_id, VideoQuestion.question_id == question_id)
        .first()
    )
    if not exists:
        db.add(VideoQuestion(video_id=video_id, question_id=question_id))
        db.commit()


DEFAULT_OUTLINE_FOCUS = {
    "public": ["理论来源与核心概念", "基本原理与方法论", "历史脉络与制度发展", "材料分析与现实应用"],
    "law": ["法律概念与法律关系", "主体权利义务与责任", "制度规则与程序适用", "案例分析与法条运用"],
    "medicine": ["基础概念与专业规范", "核心机制与临床应用", "护理药学或卫生管理要点", "病例分析与实践安全"],
    "computer": ["基础概念与系统结构", "数据处理与算法方法", "网络数据库与程序应用", "操作实践与综合应用"],
    "education": ["教育理论与发展基础", "课程教学与活动设计", "儿童学生发展与评价", "教育管理与实践反思"],
    "language": ["语言基础与文本理解", "阅读翻译与表达规则", "写作结构与语篇分析", "文学文化与综合应用"],
    "design": ["设计史论与审美基础", "形式语言与设计方法", "产品媒介与表现流程", "案例评析与创意实践"],
    "economics_management": ["基本概念与管理原理", "市场财务与组织运行", "决策分析与制度工具", "案例计算与综合应用"],
    "engineering": ["工程基础与结构原理", "材料设备与技术方法", "计算分析与施工管理", "规范应用与综合案例"],
    "public_security": ["公安司法基础理论", "制度职责与业务流程", "风险识别与处置方法", "案例研判与规范执法"],
    "professional": ["课程基础概念", "核心理论与方法", "实务流程与应用场景", "综合题型与复习归纳"],
}


def _build_default_outline(subject: Subject) -> list[dict]:
    focus_items = DEFAULT_OUTLINE_FOCUS.get(subject.category, DEFAULT_OUTLINE_FOCUS["professional"])
    chapters: list[dict] = []
    for index, focus in enumerate(focus_items, start=1):
        chapter_name = f"第{index}单元 {subject.name}：{focus}"
        chapters.append(
            {
                "name": chapter_name,
                "order": index,
                "description": (
                    f"依据 2026 年全国统考课程目录中“{subject.code} {subject.name}”建立的备考章节，"
                    f"用于章节练习、考点分析和后续线上题源生成。重点围绕{focus}组织复习。"
                ),
                "points": _build_default_points(subject, focus, index),
            }
        )
    return chapters


def _build_default_points(subject: Subject, focus: str, chapter_order: int) -> list[dict]:
    base_frequency = max(3, 9 - chapter_order)
    return [
        {
            "name": f"{subject.name}{focus}的核心概念",
            "importance": "high" if chapter_order <= 2 else "medium",
            "frequency": base_frequency,
            "description": (
                f"围绕课程代码 {subject.code} 的“{focus}”掌握基本定义、适用范围和常见表述。"
                "选择题通常考查概念边界，主观题通常要求先定义再展开要点。"
            ),
        },
        {
            "name": f"{subject.name}{focus}的关键方法",
            "importance": "high" if chapter_order in (2, 3) else "medium",
            "frequency": max(3, base_frequency - 1),
            "description": (
                f"掌握{subject.name}在“{focus}”中的分析步骤、判断依据和解题顺序。"
                "复习时应把教材术语转化为可直接书写的答题层次。"
            ),
        },
        {
            "name": f"{subject.name}{focus}的综合应用",
            "importance": "medium",
            "frequency": max(2, base_frequency - 2),
            "description": (
                f"结合{subject.name}历年自考常见题型，训练“材料定位、要点展开、结论归纳”的完整表达。"
                "该考点适合用于章节练习和考前综合复盘。"
            ),
        },
    ]


def _normalize_legacy_demo_questions(db) -> None:
    rows = db.query(Question).filter(Question.year.is_(None)).all()
    for question in rows:
        question.year = 2026
        question.month = 4 if question.month in (None, 4) else 10
        if question.source and "2026" not in question.source:
            question.source = "2026年自考备考题库（按公开教材考点整理）"
    if rows:
        db.commit()


def _deactivate_placeholder_links(db) -> None:
    rows = db.query(Video).all()
    for video in rows:
        text = " ".join(str(value or "") for value in [video.url, video.title, video.description])
        url = (video.url or "").lower()
        is_real_video = (
            "bilibili.com/video/bv" in url
            or "youtube.com/watch" in url
            or "youtu.be/" in url
            or "v.qq.com/x/" in url
            or "open.163.com/newview/movie" in url
            or "study.163.com/course/" in url
        )
        if (not is_real_video) or "example.com" in text or "占位" in text or "检索入口" in text or "官方入口" in text:
            video.is_active = 0
            video.description = "历史无效链接已停用，资源中心会在本地无匹配时线上搜索真实视频并保存。"
    if rows:
        db.commit()


SUBJECTS = [
    {
        "code": "15044",
        "old_codes": ["03709"],
        "name": "马克思主义基本原理",
        "category": "public",
        "description": (
            "2026 自学考试公共政治课。以教育部教育考试院及各省教育考试院发布的考试安排为准，"
            "学习重点覆盖马克思主义哲学、政治经济学和科学社会主义。"
        ),
        "exam_duration": 150,
        "total_score": 100,
    },
    {
        "code": "15043",
        "old_codes": ["03708"],
        "name": "中国近现代史纲要",
        "category": "public",
        "description": (
            "2026 自学考试公共政治课。围绕中国近现代历史主线、重要事件、制度变迁和历史结论组织复习。"
        ),
        "exam_duration": 150,
        "total_score": 100,
    },
]

_DETAILED_PUBLIC_SUBJECTS = {subject["code"]: subject for subject in SUBJECTS}
SUBJECTS = build_subject_seed_data()
for subject_data in SUBJECTS:
    detailed = _DETAILED_PUBLIC_SUBJECTS.get(subject_data["code"])
    if detailed:
        subject_data.update(
            {
                "old_codes": detailed.get("old_codes", subject_data.get("old_codes", [])),
                "category": detailed.get("category", subject_data.get("category")),
                "description": detailed.get("description", subject_data.get("description")),
                "exam_duration": detailed.get("exam_duration", subject_data.get("exam_duration")),
                "total_score": detailed.get("total_score", subject_data.get("total_score")),
            }
        )

CHAPTERS = {
    "15044": [
        {
            "name": "第一章 马克思主义是关于无产阶级和人类解放的科学",
            "order": 1,
            "description": "明确马克思主义的创立、发展、鲜明特征和当代价值，是后续章节的理论入口。",
            "points": [
                {
                    "name": "马克思主义的鲜明特征",
                    "importance": "high",
                    "frequency": 8,
                    "description": (
                        "重点掌握科学性、革命性、实践性、人民性、发展开放性之间的关系。答题时不要只列名词，"
                        "要说明马克思主义为什么能够指导现实实践，以及它怎样在时代发展中不断丰富。"
                    ),
                },
                {
                    "name": "马克思主义中国化时代化",
                    "importance": "high",
                    "frequency": 7,
                    "description": (
                        "理解理论必须同中国具体实际、中华优秀传统文化相结合。常见考法是辨析题或简答题，"
                        "需要从实践基础、理论创新和现实指导三个层次组织答案。"
                    ),
                },
            ],
        },
        {
            "name": "第二章 世界的物质性及发展规律",
            "order": 2,
            "description": "本章是选择题和简答题高频区域，重点在物质观、意识观、联系发展和矛盾分析法。",
            "points": [
                {
                    "name": "物质与意识的辩证关系",
                    "importance": "high",
                    "frequency": 11,
                    "description": (
                        "物质决定意识，意识对物质具有能动反作用。答题要同时写出方法论：一切从实际出发、"
                        "实事求是，并重视正确意识对实践的指导作用。易错点是把意识的能动作用理解成脱离物质条件的决定作用。"
                    ),
                },
                {
                    "name": "矛盾的普遍性和特殊性",
                    "importance": "high",
                    "frequency": 10,
                    "description": (
                        "普遍性说明矛盾存在于一切事物及其发展全过程，特殊性说明不同事物、不同阶段有不同矛盾。"
                        "论述题常要求结合具体问题具体分析，并说明普遍性寓于特殊性之中。"
                    ),
                },
                {
                    "name": "量变质变规律",
                    "importance": "medium",
                    "frequency": 6,
                    "description": (
                        "量变是质变的必要准备，质变是量变的必然结果。复习时重点区分度、关节点、渐进性和飞跃性，"
                        "并能用学习积累、制度变革等案例说明规律。"
                    ),
                },
            ],
        },
        {
            "name": "第三章 实践与认识及其发展规律",
            "order": 3,
            "description": "围绕实践、认识、真理和价值展开，是简答题与材料分析题的重要章节。",
            "points": [
                {
                    "name": "实践是认识的基础",
                    "importance": "high",
                    "frequency": 9,
                    "description": (
                        "实践产生认识需要、提供认识工具和对象、推动认识发展，并且是检验认识真理性的唯一标准。"
                        "答题时可按四点展开，再补一句认识反作用于实践。"
                    ),
                },
                {
                    "name": "真理的绝对性和相对性",
                    "importance": "medium",
                    "frequency": 6,
                    "description": (
                        "真理既有不依赖主体意志的客观内容，也受历史条件限制。常见误区是把相对真理理解成主观随意，"
                        "需要强调真理发展是由相对走向绝对的过程。"
                    ),
                },
            ],
        },
    ],
    "15043": [
        {
            "name": "第一章 反对外国侵略的斗争",
            "order": 1,
            "description": "把握近代中国社会性质变化、主要矛盾变化和民族危机加深的历史线索。",
            "points": [
                {
                    "name": "鸦片战争与中国近代史开端",
                    "importance": "high",
                    "frequency": 8,
                    "description": (
                        "鸦片战争后中国开始由封建社会逐步沦为半殖民地半封建社会。重点记忆社会性质、主要矛盾、"
                        "革命任务的变化，不要只记年份。"
                    ),
                },
                {
                    "name": "近代中国两大历史任务",
                    "importance": "high",
                    "frequency": 7,
                    "description": (
                        "争取民族独立、人民解放和实现国家富强、人民富裕是近代中国两大历史任务。二者关系是前者为后者创造前提。"
                    ),
                },
            ],
        },
        {
            "name": "第二章 对国家出路的早期探索",
            "order": 2,
            "description": "围绕太平天国、洋务运动、戊戌维新展开，重点分析探索失败原因与历史作用。",
            "points": [
                {
                    "name": "洋务运动的历史作用",
                    "importance": "medium",
                    "frequency": 6,
                    "description": (
                        "洋务运动客观上促进了近代工业、民族资本主义和新式教育的发展，但没有触动封建制度根基。"
                        "简答题通常要求同时写积极作用和失败局限。"
                    ),
                },
                {
                    "name": "戊戌维新的历史意义和局限",
                    "importance": "medium",
                    "frequency": 5,
                    "description": (
                        "戊戌维新是资产阶级改良派的政治改革尝试，推动了思想启蒙，但脱离群众、依赖皇帝且力量薄弱，最终失败。"
                    ),
                },
            ],
        },
        {
            "name": "第三章 辛亥革命与君主专制制度的终结",
            "order": 3,
            "description": "重点理解辛亥革命的历史意义、局限和旧民主主义革命终结的历史逻辑。",
            "points": [
                {
                    "name": "辛亥革命的历史意义",
                    "importance": "high",
                    "frequency": 8,
                    "description": (
                        "辛亥革命推翻清王朝，结束中国两千多年君主专制制度，传播民主共和观念。"
                        "同时要说明它没有完成反帝反封建任务。"
                    ),
                },
            ],
        },
    ],
}

QUESTIONS = {
    "15044": [
        {
            "chapter_order": 2,
            "point": "物质与意识的辩证关系",
            "content": "在物质和意识的关系问题上，马克思主义哲学认为意识的本质是（ ）。",
            "question_type": QuestionType.SINGLE_CHOICE.value,
            "options": ["人脑对客观存在的反映", "主观自生的精神实体", "脱离物质的纯粹观念", "先于实践存在的原则"],
            "answer": "A",
            "explanation": "意识是人脑的机能，是客观存在的主观映象；物质决定意识，意识又能反作用于实践。",
            "difficulty": Difficulty.EASY.value,
            "frequency": 7,
            "score": 2,
            "source": "2026年4月自考备考题库（按公开教材考点整理）",
            "month": 4,
        },
        {
            "chapter_order": 2,
            "point": "矛盾的普遍性和特殊性",
            "content": "矛盾特殊性原理要求我们在实际工作中坚持（ ）。",
            "question_type": QuestionType.SINGLE_CHOICE.value,
            "options": ["具体问题具体分析", "完全照搬已有经验", "否认矛盾普遍存在", "只看主要矛盾不看次要矛盾"],
            "answer": "A",
            "explanation": "矛盾特殊性要求分析不同事物、不同阶段、不同方面的具体特点。",
            "difficulty": Difficulty.EASY.value,
            "frequency": 8,
            "score": 2,
            "source": "2026年4月自考备考题库（高频单选）",
            "month": 4,
        },
        {
            "chapter_order": 3,
            "point": "实践是认识的基础",
            "content": "简述实践在认识发展中的基础作用。",
            "question_type": QuestionType.SHORT_ANSWER.value,
            "options": [],
            "answer": "实践产生认识需要，提供认识可能，推动认识发展，并且是检验真理的唯一标准。",
            "explanation": "答题可按四点展开：来源、动力、目的、检验标准，再说明认识反过来指导实践。",
            "difficulty": Difficulty.MEDIUM.value,
            "frequency": 7,
            "score": 6,
            "source": "2026年10月自考冲刺简答题",
            "month": 10,
        },
        {
            "chapter_order": 1,
            "point": "马克思主义中国化时代化",
            "content": "马克思主义中国化时代化的理论成果必须回答的核心问题包括（ ）。",
            "question_type": QuestionType.MULTIPLE_CHOICE.value,
            "options": ["中国实际问题", "时代发展问题", "人民实践问题", "脱离历史条件的抽象问题"],
            "answer": "ABC",
            "explanation": "理论创新必须立足中国实际、回应时代课题、总结人民实践经验。",
            "difficulty": Difficulty.MEDIUM.value,
            "frequency": 6,
            "score": 4,
            "source": "2026年4月自考备考题库（多选强化）",
            "month": 4,
        },
    ],
    "15043": [
        {
            "chapter_order": 1,
            "point": "鸦片战争与中国近代史开端",
            "content": "中国近代史以鸦片战争为开端，主要因为它导致中国社会性质开始发生重大变化，这种变化是（ ）。",
            "question_type": QuestionType.SINGLE_CHOICE.value,
            "options": ["逐步成为半殖民地半封建社会", "立即进入资本主义社会", "完全恢复封建社会稳定", "直接建立民主共和国"],
            "answer": "A",
            "explanation": "鸦片战争后，中国独立主权遭到破坏，自然经济逐步解体，社会性质发生深刻变化。",
            "difficulty": Difficulty.EASY.value,
            "frequency": 8,
            "score": 2,
            "source": "2026年4月自考备考题库（历史主线）",
            "month": 4,
        },
        {
            "chapter_order": 2,
            "point": "洋务运动的历史作用",
            "content": "洋务运动的积极作用主要表现为（ ）。",
            "question_type": QuestionType.MULTIPLE_CHOICE.value,
            "options": ["创办近代企业", "推动新式教育", "促进民族资本主义产生", "彻底改变封建制度"],
            "answer": "ABC",
            "explanation": "洋务运动没有触动封建制度根基，D 项表述错误。",
            "difficulty": Difficulty.MEDIUM.value,
            "frequency": 6,
            "score": 4,
            "source": "2026年10月自考备考题库（多选强化）",
            "month": 10,
        },
        {
            "chapter_order": 3,
            "point": "辛亥革命的历史意义",
            "content": "简述辛亥革命的历史意义及其局限。",
            "question_type": QuestionType.SHORT_ANSWER.value,
            "options": [],
            "answer": "辛亥革命推翻清王朝，结束君主专制制度，传播民主共和观念；但没有完成反帝反封建任务，也没有改变半殖民地半封建社会性质。",
            "explanation": "答题要同时写历史功绩和失败局限，避免只写推翻清朝。",
            "difficulty": Difficulty.MEDIUM.value,
            "frequency": 7,
            "score": 6,
            "source": "2026年4月自考冲刺简答题",
            "month": 4,
        },
    ],
}

VIDEOS = {
    "15044": [
        {
            "chapter_order": 2,
            "title": "B站公开课：自考马克思主义基本原理精讲",
            "url": BILIBILI_MARX_URL,
            "source": VideoSource.BILIBILI.value,
            "author": "哔哩哔哩公开资源",
            "description": "真实 B 站公开视频链接，用于马原考点精讲、冲刺和刷题复习。",
            "tags": ["2026备考", "马原", "公开视频"],
        },
    ],
    "15043": [
        {
            "chapter_order": 1,
            "title": "B站公开课：自考中国近现代史纲要精讲",
            "url": BILIBILI_HISTORY_URL,
            "source": VideoSource.BILIBILI.value,
            "author": "哔哩哔哩公开资源",
            "description": "真实 B 站公开视频链接，用于近现代史纲要章节精讲、考点串讲和冲刺复习。",
            "tags": ["2026备考", "近现代史", "公开视频"],
        },
    ],
}


def seed_demo_data() -> None:
    """Idempotently upgrade the local database to demo-ready 2026 data."""

    db = SessionLocal()
    try:
        _ensure_demo_user(db)

        subjects_by_code = {subject_data["code"]: _ensure_subject(db, subject_data) for subject_data in SUBJECTS}

        chapters_by_subject_and_order: dict[tuple[str, int], Chapter] = {}
        points_by_name: dict[str, KnowledgePoint] = {}
        for code, chapters in CHAPTERS.items():
            subject = subjects_by_code[code]
            for chapter_data in chapters:
                chapter = _ensure_chapter(db, subject.id, chapter_data)
                chapters_by_subject_and_order[(code, chapter.order)] = chapter
                for point_data in chapter_data["points"]:
                    point = _ensure_point(db, chapter.id, point_data)
                    points_by_name[point.name] = point

        for code, subject in subjects_by_code.items():
            has_chapters = db.query(Chapter.id).filter(Chapter.subject_id == subject.id).first()
            if has_chapters:
                continue
            for chapter_data in _build_default_outline(subject):
                chapter = _ensure_chapter(db, subject.id, chapter_data)
                chapters_by_subject_and_order[(code, chapter.order)] = chapter
                for point_data in chapter_data["points"]:
                    _ensure_point(db, chapter.id, point_data)

        created_questions: list[Question] = []
        for code, questions in QUESTIONS.items():
            subject = subjects_by_code[code]
            for question_data in questions:
                chapter = chapters_by_subject_and_order[(code, question_data["chapter_order"])]
                question = _ensure_question(db, subject.id, chapter.id, question_data)
                created_questions.append(question)
                point = points_by_name.get(question_data["point"])
                if point:
                    _ensure_question_point(db, question.id, point.id)

        first_question_by_subject = {}
        for question in created_questions:
            first_question_by_subject.setdefault(question.subject_id, question)

        for code, videos in VIDEOS.items():
            subject = subjects_by_code[code]
            linked_question = first_question_by_subject.get(subject.id)
            for video_data in videos:
                chapter = chapters_by_subject_and_order.get((code, video_data["chapter_order"]))
                video = _ensure_video(db, subject.id, chapter.id if chapter else None, video_data)
                if linked_question:
                    _ensure_video_question(db, video.id, linked_question.id)

        _normalize_legacy_demo_questions(db)
        _deactivate_placeholder_links(db)
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database schema...")
    init_database()
    print(f"Ensuring demo account: {DEMO_USERNAME} / {'*' * len(DEMO_PASSWORD)}")
    print("Upgrading 2026 demo data...")
    seed_demo_data()
    print("Initializing Elasticsearch index if available...")
    init_elasticsearch()
    print("Done.")
