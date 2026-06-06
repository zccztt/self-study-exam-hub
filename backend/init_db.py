# -*- coding: utf-8 -*-
"""Initialize database schema and seed demo data."""

from backend.database import SessionLocal, engine
from backend.elasticsearch_client import QUESTION_INDEX, QUESTION_INDEX_MAPPING, es_client
from backend.models import Base
from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.question import Difficulty, Question, QuestionType
from backend.models.subject import Subject
from backend.models.user import User
from backend.models.video import Video, VideoQuestion, VideoSource
from backend.utils import hash_password


def init_database() -> None:
    Base.metadata.create_all(bind=engine)


def init_elasticsearch() -> None:
    es_client.create_index(QUESTION_INDEX, QUESTION_INDEX_MAPPING)


def seed_demo_data() -> None:
    db = SessionLocal()
    try:
        if db.query(Subject).count() > 0:
            return

        user = User(
            username="demo",
            email="demo@example.com",
            hashed_password=hash_password("demo123456"),
            full_name="Demo User",
        )
        subjects = [
            Subject(
                code="03709",
                name="马克思主义基本原理概论",
                category="public",
                description="自考公共课，覆盖哲学、政治经济学和科学社会主义基础。",
                exam_duration=150,
                total_score=100,
            ),
            Subject(
                code="03708",
                name="中国近现代史纲要",
                category="public",
                description="自考公共课，梳理近现代中国历史主线和重要事件。",
                exam_duration=150,
                total_score=100,
            ),
        ]
        db.add(user)
        db.add_all(subjects)
        db.commit()

        chapters = [
            Chapter(subject_id=subjects[0].id, name="第一章 马克思主义是关于无产阶级和人类解放的科学", order=1),
            Chapter(subject_id=subjects[0].id, name="第二章 世界的物质性及发展规律", order=2),
            Chapter(subject_id=subjects[0].id, name="第三章 实践与认识及其发展规律", order=3),
            Chapter(subject_id=subjects[1].id, name="第一章 反对外国侵略的斗争", order=1),
            Chapter(subject_id=subjects[1].id, name="第二章 对国家出路的早期探索", order=2),
        ]
        db.add_all(chapters)
        db.commit()

        points = [
            KnowledgePoint(chapter_id=chapters[0].id, name="马克思主义的鲜明特征", importance="high", frequency=6),
            KnowledgePoint(chapter_id=chapters[1].id, name="物质与意识的辩证关系", importance="high", frequency=9),
            KnowledgePoint(chapter_id=chapters[1].id, name="矛盾的普遍性和特殊性", importance="high", frequency=8),
            KnowledgePoint(chapter_id=chapters[2].id, name="实践是认识的基础", importance="high", frequency=7),
            KnowledgePoint(chapter_id=chapters[3].id, name="鸦片战争与中国近代史开端", importance="medium", frequency=5),
            KnowledgePoint(chapter_id=chapters[4].id, name="洋务运动的历史作用", importance="medium", frequency=4),
        ]
        db.add_all(points)
        db.commit()

        questions = [
            Question(
                subject_id=subjects[0].id,
                chapter_id=chapters[1].id,
                content="马克思主义哲学认为，物质的唯一特性是（ ）。",
                question_type=QuestionType.SINGLE_CHOICE.value,
                options=["客观实在性", "可知性", "运动性", "实践性"],
                answer="A",
                explanation="列宁指出物质是不依赖于人的意识并能为人的意识所反映的客观实在。",
                year=2024,
                month=4,
                difficulty=Difficulty.EASY.value,
                frequency=5,
                score=2,
                source="2024年4月真题",
            ),
            Question(
                subject_id=subjects[0].id,
                chapter_id=chapters[1].id,
                content="矛盾的两个基本属性是（ ）。",
                question_type=QuestionType.MULTIPLE_CHOICE.value,
                options=["同一性", "斗争性", "普遍性", "特殊性"],
                answer="AB",
                explanation="同一性和斗争性是矛盾的两个基本属性。",
                year=2023,
                month=10,
                difficulty=Difficulty.MEDIUM.value,
                frequency=4,
                score=4,
                source="2023年10月真题",
            ),
            Question(
                subject_id=subjects[0].id,
                chapter_id=chapters[2].id,
                content="为什么说实践是认识的基础？",
                question_type=QuestionType.SHORT_ANSWER.value,
                options=[],
                answer="实践产生认识需要，提供认识可能，是检验真理的唯一标准。",
                explanation="可从实践产生认识、推动认识发展、检验认识真理性三个方面展开。",
                year=2022,
                month=4,
                difficulty=Difficulty.HARD.value,
                frequency=3,
                score=6,
                source="2022年4月真题",
            ),
            Question(
                subject_id=subjects[1].id,
                chapter_id=chapters[3].id,
                content="中国近代史的起点是（ ）。",
                question_type=QuestionType.SINGLE_CHOICE.value,
                options=["鸦片战争", "太平天国运动", "洋务运动", "戊戌维新"],
                answer="A",
                explanation="1840年鸦片战争是中国近代史的开端。",
                year=2024,
                month=4,
                difficulty=Difficulty.EASY.value,
                frequency=5,
                score=2,
                source="2024年4月真题",
            ),
            Question(
                subject_id=subjects[1].id,
                chapter_id=chapters[4].id,
                content="简述洋务运动的历史作用。",
                question_type=QuestionType.SHORT_ANSWER.value,
                options=[],
                answer="客观上促进了中国早期工业和民族资本主义发展，但没有改变封建制度根基。",
                explanation="需要同时说明积极作用和失败原因。",
                year=2023,
                month=10,
                difficulty=Difficulty.MEDIUM.value,
                frequency=4,
                score=6,
                source="2023年10月真题",
            ),
        ]
        db.add_all(questions)
        db.commit()

        links = [
            QuestionKnowledgePoint(question_id=questions[0].id, knowledge_point_id=points[1].id),
            QuestionKnowledgePoint(question_id=questions[1].id, knowledge_point_id=points[2].id),
            QuestionKnowledgePoint(question_id=questions[2].id, knowledge_point_id=points[3].id),
            QuestionKnowledgePoint(question_id=questions[3].id, knowledge_point_id=points[4].id),
            QuestionKnowledgePoint(question_id=questions[4].id, knowledge_point_id=points[5].id),
        ]
        videos = [
            Video(
                title="物质与意识的辩证关系精讲",
                url="https://example.com/videos/material-consciousness",
                source=VideoSource.CUSTOM.value,
                duration=2720,
                author="自考教研组",
                view_count=12000,
                subject_id=subjects[0].id,
                chapter_id=chapters[1].id,
                description="围绕高频考点讲解选择题和简答题作答思路。",
                tags=["哲学", "高频考点"],
            ),
            Video(
                title="中国近代史开端与鸦片战争",
                url="https://example.com/videos/opium-war",
                source=VideoSource.CUSTOM.value,
                duration=1980,
                author="自考教研组",
                view_count=8300,
                subject_id=subjects[1].id,
                chapter_id=chapters[3].id,
                description="梳理鸦片战争前后历史背景和命题点。",
                tags=["近代史", "真题"],
            ),
        ]
        db.add_all(links)
        db.add_all(videos)
        db.commit()

        db.add_all(
            [
                VideoQuestion(video_id=videos[0].id, question_id=questions[0].id),
                VideoQuestion(video_id=videos[1].id, question_id=questions[3].id),
            ]
        )
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    print("Initializing database schema...")
    init_database()
    print("Seeding demo data...")
    seed_demo_data()
    print("Initializing Elasticsearch index if available...")
    init_elasticsearch()
    print("Done.")
