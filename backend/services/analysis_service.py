# -*- coding: utf-8 -*-
"""Knowledge point analytics service."""

from collections import Counter, defaultdict
import re
from typing import Any, Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.question import Question


class AnalysisService:
    def __init__(self, db: Session):
        self.db = db

    def get_knowledge_tree(self, subject_id: int) -> Dict[str, Any]:
        chapters = (
            self.db.query(Chapter)
            .filter(Chapter.subject_id == subject_id)
            .order_by(Chapter.order.asc(), Chapter.id.asc())
            .all()
        )
        chapter_ids = [chapter.id for chapter in chapters]
        points = (
            self.db.query(KnowledgePoint)
            .filter(KnowledgePoint.chapter_id.in_(chapter_ids))
            .order_by(KnowledgePoint.frequency.desc(), KnowledgePoint.id.asc())
            .all()
            if chapter_ids
            else []
        )
        points_by_chapter: Dict[int, List[KnowledgePoint]] = defaultdict(list)
        for point in points:
            points_by_chapter[point.chapter_id].append(point)

        return {
            "subject_id": subject_id,
            "chapters": [
                {
                    "id": chapter.id,
                    "name": chapter.name,
                    "order": chapter.order,
                    "points": [
                        {
                            "id": point.id,
                            "name": point.name,
                            "description": point.description,
                            "importance": point.importance,
                            "frequency": point.frequency,
                            "detail": self._point_detail(point, chapter.name, 0),
                        }
                        for point in points_by_chapter.get(chapter.id, [])
                    ],
                }
                for chapter in chapters
            ],
        }

    def get_high_frequency_points(self, subject_id: int, limit: int = 20) -> List[Dict[str, Any]]:
        chapter_ids = [
            chapter_id
            for (chapter_id,) in self.db.query(Chapter.id).filter(Chapter.subject_id == subject_id).all()
        ]
        if not chapter_ids:
            return []

        rows = (
            self.db.query(KnowledgePoint, Chapter.name, func.count(QuestionKnowledgePoint.question_id))
            .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
            .outerjoin(
                QuestionKnowledgePoint,
                KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id,
            )
            .filter(KnowledgePoint.chapter_id.in_(chapter_ids))
            .group_by(KnowledgePoint.id, Chapter.name)
            .all()
        )
        items = [
            {
                "id": point.id,
                "name": point.name,
                "description": point.description,
                "frequency": max(point.frequency or 0, linked_count or 0),
                "importance": point.importance,
                "chapter_name": chapter_name,
                "question_count": linked_count,
                "trend": self._trend_label(subject_id, point.id),
                "detail": self._point_detail(point, chapter_name, linked_count),
            }
            for point, chapter_name, linked_count in rows
        ]
        items.sort(key=lambda item: (item["frequency"], item["question_count"], item["id"]), reverse=True)
        return items[:limit]

    def get_point_trend(self, subject_id: int, point_id: int, years: int = 5) -> Dict[str, Any]:
        rows = (
            self.db.query(Question.year, func.count(Question.id))
            .join(QuestionKnowledgePoint, Question.id == QuestionKnowledgePoint.question_id)
            .filter(
                Question.subject_id == subject_id,
                QuestionKnowledgePoint.knowledge_point_id == point_id,
                Question.year.isnot(None),
            )
            .group_by(Question.year)
            .order_by(Question.year.asc())
            .all()
        )
        values = [{"year": year, "count": count} for year, count in rows[-years:]]
        return {"subject_id": subject_id, "point_id": point_id, "values": values}

    def get_word_cloud_data(self, subject_id: int) -> List[Dict[str, Any]]:
        chapter_ids = [
            chapter_id
            for (chapter_id,) in self.db.query(Chapter.id).filter(Chapter.subject_id == subject_id).all()
        ]
        point_rows = (
            self.db.query(KnowledgePoint.name, KnowledgePoint.frequency, func.count(QuestionKnowledgePoint.question_id))
            .outerjoin(
                QuestionKnowledgePoint,
                KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id,
            )
            .filter(KnowledgePoint.chapter_id.in_(chapter_ids))
            .group_by(KnowledgePoint.id, KnowledgePoint.name, KnowledgePoint.frequency)
            .all()
            if chapter_ids
            else []
        )
        tokens: Counter[str] = Counter(
            {
                name: max(frequency or 0, linked_count or 0)
                for name, frequency, linked_count in point_rows
                if name
            }
        )
        questions = self.db.query(Question.content).filter(Question.subject_id == subject_id).all()
        stop_words = {"的", "和", "是", "在", "与", "及", "了", "A", "B", "C", "D"}
        for (content,) in questions:
            for token in re.findall(r"[\u4e00-\u9fffA-Za-z0-9]{2,}", str(content)):
                cleaned = token.strip("（）()、,.?？")
                if len(cleaned) >= 2 and cleaned not in stop_words:
                    tokens[cleaned] += 1
        return [{"word": word, "weight": weight} for word, weight in tokens.most_common(30)]

    def get_chapter_heatmap(self, subject_id: int) -> Dict[str, Any]:
        rows = (
            self.db.query(Chapter.id, Chapter.name, func.count(Question.id))
            .outerjoin(Question, Question.chapter_id == Chapter.id)
            .filter(Chapter.subject_id == subject_id)
            .group_by(Chapter.id, Chapter.name)
            .order_by(Chapter.order.asc(), Chapter.id.asc())
            .all()
        )
        return {
            "subject_id": subject_id,
            "chapters": [{"id": chapter_id, "name": name, "frequency": count} for chapter_id, name, count in rows],
        }

    def get_question_type_distribution(self, subject_id: int) -> Dict[str, Any]:
        rows = (
            self.db.query(Question.question_type, func.count(Question.id))
            .filter(Question.subject_id == subject_id)
            .group_by(Question.question_type)
            .all()
        )
        total = sum(count for _, count in rows)
        return {
            "subject_id": subject_id,
            "total": total,
            "items": [
                {
                    "question_type": question_type,
                    "count": count,
                    "percentage": round(count / total * 100, 2) if total else 0,
                }
                for question_type, count in rows
            ],
        }

    def predict_next_exam(self, subject_id: int) -> List[Dict[str, Any]]:
        points = self.get_high_frequency_points(subject_id, limit=10)
        max_frequency = max([point["frequency"] for point in points] or [1])
        return [
            {
                **point,
                "confidence": self._prediction_confidence(point, max_frequency),
                "reason": self._prediction_reason(point),
            }
            for point in points
        ]

    def _trend_label(self, subject_id: int, point_id: int) -> str:
        values = self.get_point_trend(subject_id, point_id, years=5)["values"]
        if len(values) < 2:
            return "stable"
        if values[-1]["count"] > values[0]["count"]:
            return "up"
        if values[-1]["count"] < values[0]["count"]:
            return "down"
        return "stable"

    @staticmethod
    def _prediction_confidence(point: Dict[str, Any], max_frequency: int) -> float:
        frequency_score = (point["frequency"] / max(max_frequency, 1)) * 0.35
        importance_score = 0.15 if point.get("importance") == "high" else 0.08
        trend_score = 0.1 if point.get("trend") == "up" else 0.04
        linked_score = min((point.get("question_count") or 0) / 10, 1) * 0.15
        return round(min(0.95, 0.35 + frequency_score + importance_score + trend_score + linked_score), 2)

    @staticmethod
    def _prediction_reason(point: Dict[str, Any]) -> str:
        trend_text = "近年出现频率有上升迹象" if point.get("trend") == "up" else "近年考查保持稳定"
        return (
            f"该考点累计频次 {point['frequency']}，关联训练题 {point.get('question_count') or 0} 道，"
            f"{trend_text}。建议按“概念-原理-方法论-材料应用”四步复习。"
        )

    @staticmethod
    def _point_detail(point: KnowledgePoint, chapter_name: str, linked_count: int) -> Dict[str, Any]:
        importance_label = "高频必背" if point.importance == "high" else "稳定掌握"
        base_description = point.description or "该考点需要结合教材定义、基本原理和典型材料综合理解。"
        return {
            "overview": base_description,
            "chapter_name": chapter_name,
            "importance_label": importance_label,
            "linked_question_count": linked_count,
            "exam_focus": [
                "准确写出核心概念和原理表述",
                "能区分相近概念，避免只背关键词",
                "能把原理转化为简答题或材料分析题的作答层次",
            ],
            "answer_template": [
                "第一步：点明概念或基本原理",
                "第二步：展开内在关系、方法论或历史影响",
                "第三步：结合材料或现实场景说明应用",
                "第四步：补充易错边界，形成完整结论",
            ],
            "common_mistakes": [
                "只写结论，不解释原理之间的关系",
                "把教材术语口语化，导致得分点不完整",
                "材料题脱离题干，未体现具体问题具体分析",
            ],
            "study_advice": [
                "先用 10 分钟整理概念卡片，再做 3 道对应题",
                "错题按“概念不清、审题偏差、表达缺项”三类标记",
                "考前一周用简答题模板复述，检查是否能独立成段",
            ],
        }
