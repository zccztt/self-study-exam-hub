# -*- coding: utf-8 -*-
"""Exam paper generation, session control, scoring, and wrong-book handling."""

from collections import Counter, defaultdict
import csv
import hashlib
import html
import io
import json
import math
import random
import re
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from backend.config import settings
from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.exam import Exam, ExamMode, ExamSession, ExamStatus, WrongQuestion
from backend.models.planner import UserMastery
from backend.models.question import Difficulty, Question, QuestionType
from backend.models.subject import Subject
from backend.redis_client import RedisClient
from backend.services.online_question_provider import (
    SAVED_ONLINE_SOURCE_PREFIX,
    TEMP_ONLINE_SOURCE_PREFIX,
    OnlineQuestionProvider,
)

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - optional AI grading dependency
    OpenAI = None


class ExamEngine:
    DEFAULT_QUESTION_LIMIT = 20
    MAX_QUESTION_LIMIT = 100
    ONLINE_SOURCE_FETCH_LIMIT = 20
    SCORING_RUBRIC_PATTERN = re.compile(r"\[\[SCORING_RUBRIC\]\](.*?)\[\[/SCORING_RUBRIC\]\]", re.S)
    ONLINE_QUESTION_ANGLES = [
        "核心概念解释",
        "常见选择题考法",
        "简答题答题框架",
        "案例分析应用",
        "易混淆知识点辨析",
        "复习提纲归纳",
    ]
    ONLINE_EXAM_TYPE_PATTERN = [
        {"question_type": QuestionType.SINGLE_CHOICE.value, "label": "单项选择题", "score": 2},
        {"question_type": QuestionType.SINGLE_CHOICE.value, "label": "单项选择题", "score": 2},
        {"question_type": QuestionType.SINGLE_CHOICE.value, "label": "单项选择题", "score": 2},
        {"question_type": QuestionType.SINGLE_CHOICE.value, "label": "单项选择题", "score": 2},
        {"question_type": QuestionType.MULTIPLE_CHOICE.value, "label": "多项选择题", "score": 2},
        {"question_type": QuestionType.MULTIPLE_CHOICE.value, "label": "多项选择题", "score": 2},
        {"question_type": QuestionType.FILL_BLANK.value, "label": "填空题", "score": 2},
        {"question_type": QuestionType.SHORT_ANSWER.value, "label": "简答题", "score": 6},
        {"question_type": QuestionType.ESSAY.value, "label": "论述题", "score": 10},
        {"question_type": QuestionType.CASE.value, "label": "案例分析题", "score": 10},
    ]
    QUESTION_TYPE_ORDER = {
        QuestionType.SINGLE_CHOICE.value: 0,
        QuestionType.MULTIPLE_CHOICE.value: 1,
        QuestionType.FILL_BLANK.value: 2,
        QuestionType.SHORT_ANSWER.value: 3,
        QuestionType.ESSAY.value: 4,
        QuestionType.CASE.value: 5,
    }
    DEFAULT_DIFFICULTY_RATIO = {
        Difficulty.EASY.value: 0.3,
        Difficulty.MEDIUM.value: 0.5,
        Difficulty.HARD.value: 0.2,
    }

    def __init__(
        self,
        db: Session,
        redis_client: Optional[RedisClient] = None,
        online_provider: Optional[OnlineQuestionProvider] = None,
    ):
        self.db = db
        self.redis = redis_client
        self.online_provider = online_provider or OnlineQuestionProvider()

    def generate_paper(self, subject_id: int, mode: str, config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        config = dict(config or {})
        requested_limit = self._normalize_positive_int(
            config.get("limit", config.get("question_count", self.DEFAULT_QUESTION_LIMIT)),
            default=self.DEFAULT_QUESTION_LIMIT,
            maximum=self.MAX_QUESTION_LIMIT,
        )
        duration = self._normalize_positive_int(config.get("duration", 120), default=120)
        config["limit"] = requested_limit
        config["duration"] = duration
        selected_year = None
        if mode != ExamMode.WRONG_QUESTIONS.value:
            selected_year = self._resolve_exam_year(config)
            config["year"] = selected_year
        query = self.db.query(Question).filter(
            Question.subject_id == subject_id,
            or_(Question.source.is_(None), ~Question.source.like(f"{TEMP_ONLINE_SOURCE_PREFIX}%")),
        )
        if selected_year:
            query = query.filter(Question.year == selected_year)

        if mode == ExamMode.REAL_EXAM.value:
            pass
        elif mode == ExamMode.RANDOM.value:
            if config.get("difficulty"):
                query = query.filter(Question.difficulty == config["difficulty"])
            if config.get("question_types"):
                query = query.filter(Question.question_type.in_(config["question_types"]))
        elif mode == ExamMode.CHAPTER.value and config.get("chapter_ids"):
            query = query.filter(Question.chapter_id.in_(config["chapter_ids"]))
        elif mode == ExamMode.WRONG_QUESTIONS.value and config.get("user_id"):
            wrong_query = self.db.query(WrongQuestion.question_id).filter(
                WrongQuestion.user_id == int(config["user_id"])
            )
            if not config.get("include_mastered"):
                wrong_query = wrong_query.filter(WrongQuestion.is_mastered.is_(False))
            query = query.filter(Question.id.in_(wrong_query))

        matched_questions = query.order_by(Question.year.desc().nullslast(), Question.id.asc()).all()
        available_count = len(matched_questions)
        recent_done_ids = self._recent_done_question_ids(subject_id, config)
        dedupe_relaxed = False
        if recent_done_ids and mode != ExamMode.WRONG_QUESTIONS.value:
            deduped_questions = [question for question in matched_questions if question.id not in recent_done_ids]
            if deduped_questions:
                matched_questions = deduped_questions
            else:
                dedupe_relaxed = True

        questions, constraint_report = self._select_questions_with_constraints(
            matched_questions,
            requested_limit,
            config,
        )
        constraint_report["recent_done_excluded_count"] = (
            len(recent_done_ids) if recent_done_ids and not dedupe_relaxed else 0
        )
        if dedupe_relaxed:
            constraint_report.setdefault("relaxed", []).append("近 3 年已做题去重后无可用题，已放宽去重约束。")
            constraint_report["satisfied"] = False
        shortage_message = (
            f"题库当前仅匹配 {available_count} 道题，已按实际可用数量生成。"
            if available_count < requested_limit
            else None
        )
        if constraint_report.get("relaxed"):
            relaxed_message = "部分约束因题库分布不足已按最优组合放宽。"
            shortage_message = f"{shortage_message} {relaxed_message}" if shortage_message else relaxed_message
        online_generated_count = 0
        saved_online_question_count = 0

        if not questions:
            online_result = self._build_online_questions(subject_id, mode, config, requested_limit)
            questions = online_result["questions"]
            constraint_report = self._build_constraint_report(
                selected_questions=questions,
                available_questions=questions,
                requested_limit=requested_limit,
                target_count=len(questions),
                type_targets={},
                difficulty_targets={},
                target_chapter_ids=set(),
                relaxed=["本地题库无匹配题目，已使用线上题源生成。"] if questions else [],
            )
            if not questions:
                return {
                    "exam_id": None,
                    "subject_id": subject_id,
                    "mode": mode,
                    "total_score": 0,
                    "duration": duration,
                    "requested_question_count": requested_limit,
                    "available_question_count": available_count,
                    "online_generated_count": 0,
                    "saved_online_question_count": 0,
                    "question_count": 0,
                    "questions": [],
                    "message": "没有匹配到本地题目，线上也暂未找到可生成试题的题源，请调整科目或关键词后重试。",
                    "constraint_report": constraint_report,
                }
            shortage_message = online_result["message"]
            online_generated_count = len(questions)
            saved_online_question_count = online_result["saved_count"]

        questions = self._sort_questions_by_type(questions)
        question_ids = [question.id for question in questions]
        exam = Exam(
            subject_id=subject_id,
            name=self._build_exam_name(mode, config),
            mode=mode,
            year=config.get("year"),
            month=config.get("month"),
            config=config,
            question_ids=question_ids,
            total_score=sum(question.score or 0 for question in questions),
            duration=duration,
        )
        self.db.add(exam)
        self.db.commit()
        self.db.refresh(exam)

        return {
            "exam_id": exam.id,
            "subject_id": subject_id,
            "mode": mode,
            "name": exam.name,
            "total_score": exam.total_score,
            "duration": exam.duration,
            "requested_question_count": requested_limit,
            "available_question_count": available_count,
            "online_generated_count": online_generated_count,
            "saved_online_question_count": saved_online_question_count,
            "question_count": len(questions),
            "questions": [self._serialize_exam_question(question, include_answer=False) for question in questions],
            "message": shortage_message,
            "constraint_report": constraint_report,
        }

    def _recent_done_question_ids(self, subject_id: int, config: Dict[str, Any]) -> Set[int]:
        if not config.get("avoid_recent_done", config.get("avoidRecentDone", True)):
            return set()
        user_id = config.get("user_id")
        if not user_id:
            return set()
        try:
            parsed_user_id = int(user_id)
        except (TypeError, ValueError):
            return set()

        lookback_years = self._normalize_positive_int(
            config.get("recent_done_years", config.get("recentDoneYears", 3)),
            default=3,
            maximum=10,
        )
        cutoff_time = datetime.now() - timedelta(days=365 * lookback_years)
        sessions = (
            self.db.query(ExamSession, Exam)
            .join(Exam, ExamSession.exam_id == Exam.id)
            .filter(
                ExamSession.user_id == parsed_user_id,
                Exam.subject_id == subject_id,
                ExamSession.status == ExamStatus.COMPLETED.value,
                or_(
                    ExamSession.submitted_at >= cutoff_time,
                    and_(ExamSession.submitted_at.is_(None), ExamSession.start_time >= cutoff_time),
                ),
            )
            .all()
        )

        question_ids: Set[int] = set()
        for _, exam in sessions:
            for question_id in exam.question_ids or []:
                try:
                    question_ids.add(int(question_id))
                except (TypeError, ValueError):
                    continue
        return question_ids

    def _select_questions_with_constraints(
        self,
        available_questions: List[Question],
        requested_limit: int,
        config: Dict[str, Any],
    ) -> Tuple[List[Question], Dict[str, Any]]:
        target_count = min(requested_limit, len(available_questions))
        if target_count <= 0:
            return [], self._build_constraint_report(
                selected_questions=[],
                available_questions=available_questions,
                requested_limit=requested_limit,
                target_count=0,
                type_targets={},
                difficulty_targets={},
                target_chapter_ids=set(),
                relaxed=[],
            )

        constraints = self._constraint_config(config)
        type_capacities = Counter(question.question_type for question in available_questions)
        difficulty_capacities = Counter(
            question.difficulty or Difficulty.MEDIUM.value for question in available_questions
        )
        chapter_capacities = Counter(
            question.chapter_id for question in available_questions if question.chapter_id is not None
        )
        type_targets = self._build_group_targets(
            total=target_count,
            capacities=dict(type_capacities),
            count_map=self._constraint_number_map(
                constraints,
                ["question_type_counts", "questionTypeCounts", "type_counts"],
            ),
            ratio_map=self._constraint_number_map(
                constraints,
                [
                    "question_type_ratio",
                    "question_type_ratios",
                    "question_type_distribution",
                    "questionTypeRatio",
                    "questionTypeRatios",
                ],
            ),
            default_weights=dict(type_capacities),
        )
        difficulty_targets = self._build_group_targets(
            total=target_count,
            capacities=dict(difficulty_capacities),
            count_map=self._constraint_number_map(
                constraints,
                ["difficulty_counts", "difficultyCounts"],
            ),
            ratio_map=self._constraint_number_map(
                constraints,
                [
                    "difficulty_ratio",
                    "difficulty_ratios",
                    "difficulty_distribution",
                    "difficultyRatio",
                    "difficultyRatios",
                ],
            ),
            default_weights=self.DEFAULT_DIFFICULTY_RATIO,
        )
        target_chapter_ids = self._target_chapter_ids(
            config=constraints,
            target_count=target_count,
            chapter_capacities=chapter_capacities,
        )

        selected: List[Question] = []
        selected_ids: Set[int] = set()
        selected_types: Counter[str] = Counter()
        selected_difficulties: Counter[str] = Counter()
        selected_chapters: Counter[int] = Counter()
        relaxed: List[str] = []
        max_frequency = max([question.frequency or 0 for question in available_questions] or [1])
        years = [question.year for question in available_questions if question.year]
        min_year = min(years) if years else None
        max_year = max(years) if years else None

        while len(selected) < target_count:
            remaining = [question for question in available_questions if question.id not in selected_ids]
            if not remaining:
                break

            remaining_slots_after = target_count - len(selected) - 1
            feasible = [
                question
                for question in remaining
                if self._candidate_keeps_constraints(
                    question=question,
                    remaining_slots_after=remaining_slots_after,
                    selected_types=selected_types,
                    selected_difficulties=selected_difficulties,
                    selected_chapters=selected_chapters,
                    type_targets=type_targets,
                    difficulty_targets=difficulty_targets,
                    target_chapter_ids=target_chapter_ids,
                )
            ]
            if not feasible:
                feasible = remaining
                if not relaxed:
                    relaxed.append("题型、难度和章节覆盖约束存在组合冲突。")

            chosen = max(
                feasible,
                key=lambda question: self._constraint_greedy_score(
                    question=question,
                    selected_types=selected_types,
                    selected_difficulties=selected_difficulties,
                    selected_chapters=selected_chapters,
                    type_targets=type_targets,
                    difficulty_targets=difficulty_targets,
                    target_chapter_ids=target_chapter_ids,
                    max_frequency=max_frequency,
                    min_year=min_year,
                    max_year=max_year,
                ),
            )
            selected.append(chosen)
            selected_ids.add(chosen.id)
            selected_types[chosen.question_type] += 1
            selected_difficulties[chosen.difficulty or Difficulty.MEDIUM.value] += 1
            if chosen.chapter_id is not None:
                selected_chapters[chosen.chapter_id] += 1

        report = self._build_constraint_report(
            selected_questions=selected,
            available_questions=available_questions,
            requested_limit=requested_limit,
            target_count=target_count,
            type_targets=type_targets,
            difficulty_targets=difficulty_targets,
            target_chapter_ids=target_chapter_ids,
            relaxed=relaxed,
        )
        if not report["satisfied"] and not report["relaxed"]:
            report["relaxed"].append("题库题目分布无法完全满足所有目标配比。")
        return selected, report

    @classmethod
    def _constraint_config(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        constraints = dict(config)
        nested = config.get("constraints")
        if isinstance(nested, dict):
            constraints.update(nested)
        return constraints

    @staticmethod
    def _constraint_number_map(config: Dict[str, Any], keys: List[str]) -> Dict[str, float]:
        for key in keys:
            raw_value = config.get(key)
            if not isinstance(raw_value, dict):
                continue
            parsed: Dict[str, float] = {}
            for item_key, item_value in raw_value.items():
                try:
                    number = float(item_value)
                except (TypeError, ValueError):
                    continue
                if number > 0:
                    parsed[str(item_key)] = number
            if parsed:
                return parsed
        return {}

    @classmethod
    def _build_group_targets(
        cls,
        *,
        total: int,
        capacities: Dict[str, int],
        count_map: Dict[str, float],
        ratio_map: Dict[str, float],
        default_weights: Dict[str, float],
    ) -> Dict[str, int]:
        active_capacities = {
            str(key): int(value)
            for key, value in capacities.items()
            if value and int(value) > 0
        }
        if total <= 0 or not active_capacities:
            return {}

        targets = {key: 0 for key in active_capacities}
        if count_map:
            requested = {
                key: int(round(value))
                for key, value in count_map.items()
                if key in active_capacities and value > 0
            }
            requested_total = sum(requested.values())
            if requested_total > total:
                targets = cls._largest_remainder_targets(total, requested, active_capacities)
            else:
                for key, value in requested.items():
                    targets[key] = min(value, active_capacities[key])
        else:
            weights = ratio_map or default_weights
            targets = cls._largest_remainder_targets(total, weights, active_capacities)

        selected_total = sum(targets.values())
        if selected_total < total:
            spare_capacities = {
                key: capacity - targets.get(key, 0)
                for key, capacity in active_capacities.items()
                if capacity > targets.get(key, 0)
            }
            fill_weights = {
                key: ratio_map.get(key) or default_weights.get(key) or spare_capacities[key]
                for key in spare_capacities
            }
            extra_targets = cls._largest_remainder_targets(total - selected_total, fill_weights, spare_capacities)
            for key, value in extra_targets.items():
                targets[key] = targets.get(key, 0) + value

        return {key: value for key, value in targets.items() if value > 0}

    @staticmethod
    def _largest_remainder_targets(
        total: int,
        weights: Dict[str, float],
        capacities: Dict[str, int],
    ) -> Dict[str, int]:
        active_weights = {
            key: max(float(weights.get(key, 0)), 0.0)
            for key in capacities
            if capacities[key] > 0
        }
        if not any(active_weights.values()):
            active_weights = {key: float(capacity) for key, capacity in capacities.items() if capacity > 0}
        weight_total = sum(active_weights.values())
        if total <= 0 or weight_total <= 0:
            return {key: 0 for key in capacities}

        targets: Dict[str, int] = {}
        remainders: List[Tuple[float, float, int, str]] = []
        for key, capacity in capacities.items():
            raw_target = total * (active_weights.get(key, 0.0) / weight_total)
            base_target = min(capacity, int(math.floor(raw_target)))
            targets[key] = base_target
            remainders.append((raw_target - base_target, active_weights.get(key, 0.0), capacity, key))

        remaining = total - sum(targets.values())
        while remaining > 0:
            candidates = [
                (remainder, weight, capacity, key)
                for remainder, weight, capacity, key in remainders
                if targets.get(key, 0) < capacity
            ]
            if not candidates:
                break
            _, _, _, key = max(candidates)
            targets[key] += 1
            remaining -= 1
        return targets

    @staticmethod
    def _target_chapter_ids(
        *,
        config: Dict[str, Any],
        target_count: int,
        chapter_capacities: Counter,
    ) -> Set[int]:
        raw_coverage = config.get("chapter_coverage", config.get("chapterCoverage", 0))
        try:
            coverage = float(raw_coverage)
        except (TypeError, ValueError):
            coverage = 0.0
        if coverage > 1:
            coverage = coverage / 100
        coverage = max(0.0, min(1.0, coverage))
        if coverage <= 0 or target_count <= 0:
            return set()

        raw_scope = config.get("chapter_ids") or config.get("chapterIds")
        scope: List[int] = []
        if isinstance(raw_scope, list):
            for item in raw_scope:
                try:
                    scope.append(int(item))
                except (TypeError, ValueError):
                    continue
        available_chapters = [
            chapter_id
            for chapter_id in (scope or list(chapter_capacities.keys()))
            if chapter_capacities.get(chapter_id, 0) > 0
        ]
        if not available_chapters:
            return set()

        target_chapter_count = min(
            target_count,
            len(available_chapters),
            max(1, int(math.ceil(len(available_chapters) * coverage))),
        )
        ranked_chapters = sorted(
            available_chapters,
            key=lambda chapter_id: (-chapter_capacities.get(chapter_id, 0), chapter_id),
        )
        return set(ranked_chapters[:target_chapter_count])

    @staticmethod
    def _candidate_keeps_constraints(
        *,
        question: Question,
        remaining_slots_after: int,
        selected_types: Counter,
        selected_difficulties: Counter,
        selected_chapters: Counter,
        type_targets: Dict[str, int],
        difficulty_targets: Dict[str, int],
        target_chapter_ids: Set[int],
    ) -> bool:
        question_type = question.question_type
        difficulty = question.difficulty or Difficulty.MEDIUM.value
        type_missing = 0
        for key, target in type_targets.items():
            after_count = selected_types.get(key, 0) + (1 if key == question_type else 0)
            type_missing += max(target - after_count, 0)

        difficulty_missing = 0
        for key, target in difficulty_targets.items():
            after_count = selected_difficulties.get(key, 0) + (1 if key == difficulty else 0)
            difficulty_missing += max(target - after_count, 0)

        covered_chapters = {
            chapter_id for chapter_id in selected_chapters if chapter_id in target_chapter_ids
        }
        if question.chapter_id in target_chapter_ids:
            covered_chapters.add(question.chapter_id)
        chapter_missing = max(len(target_chapter_ids) - len(covered_chapters), 0)

        return (
            type_missing <= remaining_slots_after
            and difficulty_missing <= remaining_slots_after
            and chapter_missing <= remaining_slots_after
        )

    @staticmethod
    def _constraint_greedy_score(
        *,
        question: Question,
        selected_types: Counter,
        selected_difficulties: Counter,
        selected_chapters: Counter,
        type_targets: Dict[str, int],
        difficulty_targets: Dict[str, int],
        target_chapter_ids: Set[int],
        max_frequency: int,
        min_year: Optional[int],
        max_year: Optional[int],
    ) -> float:
        question_type = question.question_type
        difficulty = question.difficulty or Difficulty.MEDIUM.value
        score = 0.0

        type_target = type_targets.get(question_type, 0)
        type_deficit = type_target - selected_types.get(question_type, 0)
        score += 90 + type_deficit * 8 if type_deficit > 0 else -25 * abs(type_deficit)

        difficulty_target = difficulty_targets.get(difficulty, 0)
        difficulty_deficit = difficulty_target - selected_difficulties.get(difficulty, 0)
        score += 80 + difficulty_deficit * 7 if difficulty_deficit > 0 else -20 * abs(difficulty_deficit)

        if target_chapter_ids:
            if question.chapter_id in target_chapter_ids and selected_chapters.get(question.chapter_id, 0) == 0:
                score += 120
            elif question.chapter_id in target_chapter_ids:
                score += max(0, 30 - selected_chapters.get(question.chapter_id, 0) * 8)
            else:
                score -= 20
        elif question.chapter_id is not None:
            score -= selected_chapters.get(question.chapter_id, 0) * 4

        frequency = max(question.frequency or 0, 0)
        score += (frequency / max(max_frequency, 1)) * 20
        if question.year and min_year is not None and max_year is not None and max_year > min_year:
            score += ((question.year - min_year) / (max_year - min_year)) * 8
        elif question.year:
            score += 4
        score += (question.score or 0) * 0.4
        score -= (question.id or 0) * 0.000001
        return score

    @staticmethod
    def _build_constraint_report(
        *,
        selected_questions: List[Question],
        available_questions: List[Question],
        requested_limit: int,
        target_count: int,
        type_targets: Dict[str, int],
        difficulty_targets: Dict[str, int],
        target_chapter_ids: Set[int],
        relaxed: List[str],
    ) -> Dict[str, Any]:
        actual_types = Counter(question.question_type for question in selected_questions)
        actual_difficulties = Counter(
            question.difficulty or Difficulty.MEDIUM.value for question in selected_questions
        )
        covered_chapters = {
            question.chapter_id
            for question in selected_questions
            if question.chapter_id is not None
        }
        available_chapters = {
            question.chapter_id
            for question in available_questions
            if question.chapter_id is not None
        }
        target_chapter_count = len(target_chapter_ids)
        actual_target_coverage = len(covered_chapters & target_chapter_ids)
        actual_chapter_coverage = (
            round(len(covered_chapters) / len(available_chapters), 4)
            if available_chapters
            else 0.0
        )
        type_satisfied = all(actual_types.get(key, 0) >= target for key, target in type_targets.items())
        difficulty_satisfied = all(
            actual_difficulties.get(key, 0) >= target for key, target in difficulty_targets.items()
        )
        chapter_satisfied = actual_target_coverage >= target_chapter_count
        count_satisfied = len(selected_questions) == target_count
        relaxed_items = list(relaxed)
        if not type_satisfied:
            relaxed_items.append("题型配比未完全满足。")
        if not difficulty_satisfied:
            relaxed_items.append("难度配比未完全满足。")
        if not chapter_satisfied:
            relaxed_items.append("章节覆盖未完全满足。")
        if not count_satisfied:
            relaxed_items.append("题目数量未达到目标。")

        return {
            "algorithm": "constraint_greedy_v1",
            "requested_count": requested_limit,
            "target_count": target_count,
            "selected_count": len(selected_questions),
            "available_count": len(available_questions),
            "question_type_target": dict(type_targets),
            "question_type_actual": dict(actual_types),
            "difficulty_target": dict(difficulty_targets),
            "difficulty_actual": dict(actual_difficulties),
            "chapter_coverage_target_count": target_chapter_count,
            "chapter_coverage_actual_count": actual_target_coverage,
            "chapter_coverage_actual": actual_chapter_coverage,
            "covered_chapter_ids": sorted(covered_chapters),
            "target_chapter_ids": sorted(target_chapter_ids),
            "satisfied": not relaxed_items,
            "relaxed": relaxed_items,
        }

    def _build_online_questions(
        self,
        subject_id: int,
        mode: str,
        config: Dict[str, Any],
        requested_limit: int,
    ) -> Dict[str, Any]:
        if mode == ExamMode.WRONG_QUESTIONS.value or not config.get("online_fallback", True):
            return {"questions": [], "message": None, "saved_count": 0}

        subject = self.db.query(Subject).filter(Subject.id == subject_id).first()
        if not subject:
            return {"questions": [], "message": None, "saved_count": 0}

        should_save = bool(config.get("save_online_questions"))
        keyword = self._build_online_search_keyword(subject, mode, config)
        online_items = self.online_provider.search(
            subject_id=subject.id,
            subject_code=subject.code,
            subject_name=subject.name,
            keyword=keyword,
            year=config.get("year"),
            limit=min(requested_limit, self.ONLINE_SOURCE_FETCH_LIMIT),
        )
        questions: List[Question] = []
        for online_item in self._expand_online_items(online_items, requested_limit):
            question_spec = self._build_online_question_spec(len(questions))
            question = self._create_online_question(
                subject=subject,
                online_item=online_item,
                config=config,
                should_save=should_save,
                question_spec=question_spec,
            )
            if question:
                questions.append(question)
            if len(questions) >= requested_limit:
                break

        if not questions:
            return {"questions": [], "message": None, "saved_count": 0}

        save_label = "已存入题库，后续组卷将直接复用。" if should_save else "本次作为临时试题使用，未进入题库。"
        return {
            "questions": questions,
            "message": f"本地题库暂无匹配题目，已根据线上题源生成 {len(questions)} 道试题；{save_label}",
            "saved_count": len(questions) if should_save else 0,
        }

    def _expand_online_items(self, online_items: List[Dict[str, Any]], requested_limit: int) -> List[Dict[str, Any]]:
        if not online_items:
            return []

        expanded: List[Dict[str, Any]] = []
        for index in range(requested_limit):
            item = dict(online_items[index % len(online_items)])
            cycle = index // len(online_items)
            item["_variant_index"] = cycle + 1
            item["_variant_angle"] = self.ONLINE_QUESTION_ANGLES[index % len(self.ONLINE_QUESTION_ANGLES)]
            expanded.append(item)
        return expanded

    def _create_online_question(
        self,
        *,
        subject: Subject,
        online_item: Dict[str, Any],
        config: Dict[str, Any],
        should_save: bool,
        question_spec: Dict[str, Any],
    ) -> Optional[Question]:
        source_url = str(online_item.get("source_url") or "").strip()
        raw_content = str(online_item.get("content") or "").strip()
        if not source_url or not raw_content:
            return None

        variant_index = self._normalize_positive_int(online_item.get("_variant_index", 1), default=1)
        variant_angle = str(online_item.get("_variant_angle") or self.ONLINE_QUESTION_ANGLES[0])
        question_type = str(question_spec["question_type"])
        target_year = self._resolve_exam_year(config)
        fingerprint = hashlib.sha1(
            f"{subject.code}|{target_year}|{source_url}|{variant_index}|{variant_angle}|{question_type}".encode("utf-8")
        ).hexdigest()[:12]
        source_prefix = SAVED_ONLINE_SOURCE_PREFIX if should_save else TEMP_ONLINE_SOURCE_PREFIX
        title, snippet = self._split_online_content(raw_content)
        payload = self._build_online_question_payload(
            subject=subject,
            title=title,
            snippet=snippet,
            variant_angle=variant_angle,
            source_url=source_url,
            fingerprint=fingerprint,
            question_spec=question_spec,
        )
        existing = (
            self.db.query(Question)
            .filter(Question.subject_id == subject.id, Question.content.like(f"%题源编号：{fingerprint}%"))
            .first()
        )
        if existing and (should_save or not (existing.source or "").startswith(SAVED_ONLINE_SOURCE_PREFIX)):
            if should_save and (existing.source or "").startswith(TEMP_ONLINE_SOURCE_PREFIX):
                existing.source = f"{SAVED_ONLINE_SOURCE_PREFIX}：{online_item.get('source') or '实时搜索'}"
                existing.frequency = max(existing.frequency or 0, 1)
            self._apply_online_question_payload(existing, payload, year=target_year)
            self.db.flush()
            return existing

        chapter_id = self._resolve_generated_chapter_id(config)

        question = Question(
            subject_id=subject.id,
            chapter_id=chapter_id,
            content=payload["content"],
            question_type=payload["question_type"],
            options=payload["options"],
            answer=payload["answer"],
            explanation=payload["explanation"],
            year=target_year,
            month=config.get("month"),
            difficulty=Difficulty.MEDIUM.value,
            frequency=1 if should_save else 0,
            score=payload["score"],
            source=f"{source_prefix}：{online_item.get('source') or '实时搜索'}",
        )
        self.db.add(question)
        self.db.flush()
        return question

    def _build_online_question_payload(
        self,
        *,
        subject: Subject,
        title: str,
        snippet: str,
        variant_angle: str,
        source_url: str,
        fingerprint: str,
        question_spec: Dict[str, Any],
    ) -> Dict[str, Any]:
        subject_name = subject.name or "本课程"
        subject_code = subject.code or "-"
        title_text = self._clean_online_text(title, limit=120, fallback="线上题源")
        snippet_text = self._clean_online_text(snippet, limit=260)
        focus_text = self._clean_online_text(title_text or snippet_text, limit=48, fallback=subject_name)
        question_type = str(question_spec["question_type"])
        score = int(question_spec["score"])
        label = str(question_spec["label"])

        if question_type == QuestionType.SINGLE_CHOICE.value:
            stem, options, answer, scoring_points = self._build_online_single_choice(
                subject_name=subject_name,
                subject_code=subject_code,
                title_text=title_text,
                snippet_text=snippet_text,
                focus_text=focus_text,
                variant_angle=variant_angle,
                fingerprint=fingerprint,
                score=score,
            )
        elif question_type == QuestionType.MULTIPLE_CHOICE.value:
            stem, options, answer, scoring_points = self._build_online_multiple_choice(
                subject_name=subject_name,
                subject_code=subject_code,
                title_text=title_text,
                focus_text=focus_text,
                variant_angle=variant_angle,
                fingerprint=fingerprint,
                score=score,
            )
        elif question_type == QuestionType.FILL_BLANK.value:
            stem, options, answer, scoring_points = self._build_online_fill_blank(
                subject_name=subject_name,
                focus_text=focus_text,
                variant_angle=variant_angle,
                score=score,
            )
        else:
            stem, options, answer, scoring_points = self._build_online_subjective_question(
                question_type=question_type,
                subject_name=subject_name,
                subject_code=subject_code,
                title_text=title_text,
                snippet_text=snippet_text,
                focus_text=focus_text,
                variant_angle=variant_angle,
                score=score,
            )

        content = (
            f"【线上生成】{subject_name}（课程代码 {subject_code}）{label}\n"
            f"题源编号：{fingerprint}\n"
            f"题源标题：{title_text}\n"
            f"训练角度：{variant_angle}\n"
            f"题干：{stem}"
        )
        if snippet_text:
            content += f"\n题源摘要：{snippet_text}"

        rubric = {
            "version": 1,
            "auto_score": True,
            "question_type": question_type,
            "source_url": source_url,
            "scoring_points": scoring_points,
        }
        if question_type in {QuestionType.SINGLE_CHOICE.value, QuestionType.MULTIPLE_CHOICE.value, QuestionType.FILL_BLANK.value}:
            explanation_text = (
                f"本题标准答案为 {answer}。解题时应围绕题源“{title_text}”定位{subject_name}的核心考点，"
                "再判断选项或空缺内容是否符合课程概念、适用条件和考试大纲表述。"
            )
        else:
            explanation_text = (
                f"参考答案：{answer}\n"
                "评分说明：系统会按下列评分项自动评分，重点考查概念定位、要点展开、结合题源和表达完整性。"
            )
        explanation = (
            f"{explanation_text}\n题源链接：{source_url}\n"
            f"评分项：{self._format_scoring_points(scoring_points)}\n"
            f"[[SCORING_RUBRIC]]{json.dumps(rubric, ensure_ascii=False)}[[/SCORING_RUBRIC]]"
        )
        return {
            "question_type": question_type,
            "content": content,
            "options": options,
            "answer": answer,
            "explanation": explanation,
            "score": score,
        }

    def _build_online_single_choice(
        self,
        *,
        subject_name: str,
        subject_code: str,
        title_text: str,
        snippet_text: str,
        focus_text: str,
        variant_angle: str,
        fingerprint: str,
        score: int,
    ) -> tuple[str, List[str], str, List[Dict[str, Any]]]:
        stem = (
            f"根据题源“{title_text}”"
            f"{'及其摘要' if snippet_text else ''}，以下哪项最适合作为{subject_name}"
            f"（课程代码 {subject_code}）“{variant_angle}”的作答方向？"
        )
        correct_option, distractors = self._build_online_choice_options(
            subject_name=subject_name,
            subject_code=subject_code,
            focus_text=focus_text,
            variant_angle=variant_angle,
        )
        options, answer = self._position_correct_option(
            correct_option=correct_option,
            distractors=distractors,
            seed=f"{fingerprint}|single|{variant_angle}",
        )
        return stem, options, answer, [
            self._scoring_point("选出唯一正确选项", score, [answer, correct_option])
        ]

    def _build_online_multiple_choice(
        self,
        *,
        subject_name: str,
        subject_code: str,
        title_text: str,
        focus_text: str,
        variant_angle: str,
        fingerprint: str,
        score: int,
    ) -> tuple[str, List[str], str, List[Dict[str, Any]]]:
        correct_one, distractors = self._build_online_choice_options(
            subject_name=subject_name,
            subject_code=subject_code,
            focus_text=focus_text,
            variant_angle=variant_angle,
        )
        correct_two = f"结合{subject_name}考试大纲，将“{focus_text}”拆解为概念、条件、应用和易错点复习。"
        options, answer = self._position_multiple_correct_options(
            correct_options=[correct_one, correct_two],
            distractors=distractors,
            seed=f"{fingerprint}|multiple|{variant_angle}",
        )
        stem = f"关于题源“{title_text}”对应考点的复习和作答，下列说法正确的有哪几项？"
        return stem, options, answer, [
            self._scoring_point("完整选出全部正确选项且不多选", score, [answer, correct_one, correct_two])
        ]

    @staticmethod
    def _build_online_fill_blank(
        *,
        subject_name: str,
        focus_text: str,
        variant_angle: str,
        score: int,
    ) -> tuple[str, List[str], str, List[Dict[str, Any]]]:
        stem = (
            f"{subject_name}复习“{focus_text}”时，应先定位核心概念，再归纳其____、适用条件和易错边界。"
        )
        answer = "主要特征|基本特征|核心特征"
        return stem, [], answer, [
            ExamEngine._scoring_point("填写与“主要特征”同义的关键词", score, ["主要特征", "基本特征", "核心特征"])
        ]

    @staticmethod
    def _build_online_subjective_question(
        *,
        question_type: str,
        subject_name: str,
        subject_code: str,
        title_text: str,
        snippet_text: str,
        focus_text: str,
        variant_angle: str,
        score: int,
    ) -> tuple[str, List[str], str, List[Dict[str, Any]]]:
        if question_type == QuestionType.CASE.value:
            stem = (
                f"结合题源“{title_text}”中的线索，围绕“{focus_text}”设计一个{subject_name}"
                f"（课程代码 {subject_code}）案例分析答题思路。要求指出问题情境、适用原理、分析过程和结论建议。"
            )
            answer = (
                f"应先概括题源情境，说明其涉及“{focus_text}”相关知识；再匹配{subject_name}教材中的核心原理；"
                "随后按原因、表现、影响和对策展开分析；最后给出清晰结论，并提示易错边界。"
            )
            point_weights = [3, 3, 2, 2]
            labels = [
                "概括案例情境并点明考点",
                "准确调用课程原理或概念",
                "结合材料展开原因、表现或影响分析",
                "形成结论、建议或风险提示",
            ]
        elif question_type == QuestionType.ESSAY.value:
            stem = (
                f"论述题源“{title_text}”反映的“{focus_text}”考点在{subject_name}复习中的作用。"
                "要求观点明确、层次完整，并结合概念、条件、应用和易错点展开。"
            )
            answer = (
                f"应围绕“{focus_text}”提出明确观点，先界定相关概念，再说明构成要点或适用条件；"
                "进一步联系课程大纲阐述应用场景、命题方式和易错边界，最后归纳复习价值。"
            )
            point_weights = [2, 3, 3, 2]
            labels = [
                "观点明确并准确界定核心概念",
                "展开构成要点、适用条件或判断标准",
                "联系课程应用、命题方式或易错边界",
                "结构完整、表达条理清晰",
            ]
        else:
            stem = (
                f"简述题源“{title_text}”对应的“{focus_text}”考点。"
                "要求说明概念含义、答题要点、常见考法和复习注意事项。"
            )
            answer = (
                f"应说明“{focus_text}”的基本含义，提炼与{subject_name}课程相关的关键要点；"
                "结合题源信息指出常见考法，并补充复习时需要区分的易混点。"
            )
            point_weights = [2, 2, 1, 1] if score <= 6 else [3, 3, 2, 2]
            labels = [
                "准确说明核心概念或基本含义",
                "提炼两个以上关键答题要点",
                "结合题源或课程大纲说明常见考法",
                "指出易错点或复习注意事项",
            ]

        keywords = ExamEngine._rubric_keywords(
            subject_name=subject_name,
            focus_text=focus_text,
            title_text=title_text,
            snippet_text=snippet_text,
        )
        scoring_points = []
        for index, (label, weight) in enumerate(zip(labels, point_weights)):
            scoring_points.append(
                ExamEngine._scoring_point(
                    label,
                    weight,
                    keywords[index % len(keywords)] + keywords[-1:],
                )
            )
        return stem, [], answer, scoring_points

    @staticmethod
    def _build_online_choice_options(
        *,
        subject_name: str,
        subject_code: str,
        focus_text: str,
        variant_angle: str,
    ) -> tuple[str, List[str]]:
        correct_by_angle = {
            "核心概念解释": f"围绕“{focus_text}”界定核心概念，并说明定义、特征、适用条件和易错边界。",
            "常见选择题考法": f"抓住“{focus_text}”涉及的定义关键词、适用条件和易混选项差异。",
            "简答题答题框架": f"按“概念界定—要点展开—应用场景—结论归纳”的层次整理“{focus_text}”。",
            "案例分析应用": f"从“{focus_text}”提取问题情境，再匹配{subject_name}的课程原理分析原因和对策。",
            "易混淆知识点辨析": f"比较“{focus_text}”相关概念的定义边界、构成要件和典型适用情境。",
            "复习提纲归纳": f"围绕“{focus_text}”建立概念、重点题型、易错原因和复盘路径。",
        }
        correct_option = correct_by_angle.get(
            variant_angle,
            f"结合“{focus_text}”提炼{subject_name}的核心概念、命题条件和答题要点。",
        )
        distractors = [
            f"只记录“{focus_text}”的网页标题或来源，不再回到教材和考试大纲核对。",
            f"直接背诵搜索摘要全文，不区分{subject_name}的概念、条件、应用与易错点。",
            "只根据搜索结果排名判断考试重点，把经验性表述直接当成标准答案。",
            f"忽略课程代码 {subject_code}，按任意自考科目的通用模板作答。",
        ]
        return correct_option, distractors

    @staticmethod
    def _position_correct_option(
        *,
        correct_option: str,
        distractors: List[str],
        seed: str,
    ) -> tuple[List[str], str]:
        clean_options: List[str] = []
        seen = set()
        for option in [*distractors, correct_option]:
            normalized = re.sub(r"\s+", "", option)
            if normalized in seen:
                continue
            seen.add(normalized)
            clean_options.append(option)

        while len(clean_options) < 3:
            clean_options.append("无法对应课程大纲中的具体知识点和答题要求。")

        clean_distractors = [option for option in clean_options if option != correct_option][:3]
        correct_index = int(hashlib.sha1(seed.encode("utf-8")).hexdigest()[:2], 16) % 4
        options = clean_distractors[:]
        options.insert(correct_index, correct_option)
        return options[:4], "ABCD"[correct_index]

    @staticmethod
    def _position_multiple_correct_options(
        *,
        correct_options: List[str],
        distractors: List[str],
        seed: str,
    ) -> tuple[List[str], str]:
        option_items = [{"text": text, "correct": True} for text in correct_options[:2]]
        option_items.extend({"text": text, "correct": False} for text in distractors[:2])
        random.Random(seed).shuffle(option_items)
        letters: List[str] = []
        for index, item in enumerate(option_items[:4]):
            if item["correct"]:
                letters.append("ABCD"[index])
        return [str(item["text"]) for item in option_items[:4]], "".join(letters)

    @staticmethod
    def _apply_online_question_payload(question: Question, payload: Dict[str, Any], *, year: Optional[int] = None) -> None:
        question.content = payload["content"]
        question.question_type = payload["question_type"]
        question.options = payload["options"]
        question.answer = payload["answer"]
        question.explanation = payload["explanation"]
        question.year = year or ExamEngine._resolve_exam_year({})
        question.difficulty = Difficulty.MEDIUM.value
        question.score = payload["score"]

    @staticmethod
    def _build_online_question_spec(index: int) -> Dict[str, Any]:
        spec = ExamEngine.ONLINE_EXAM_TYPE_PATTERN[index % len(ExamEngine.ONLINE_EXAM_TYPE_PATTERN)]
        return dict(spec)

    @classmethod
    def _sort_questions_by_type(cls, questions: List[Question]) -> List[Question]:
        indexed_questions = list(enumerate(questions))
        indexed_questions.sort(
            key=lambda item: (
                cls.QUESTION_TYPE_ORDER.get(item[1].question_type, len(cls.QUESTION_TYPE_ORDER)),
                item[0],
            )
        )
        return [question for _, question in indexed_questions]

    @staticmethod
    def _scoring_point(label: str, score: int, keywords: List[str]) -> Dict[str, Any]:
        clean_keywords = [
            re.sub(r"\s+", "", str(keyword)).strip()
            for keyword in keywords
            if str(keyword or "").strip()
        ]
        return {
            "label": label,
            "score": score,
            "keywords": list(dict.fromkeys(clean_keywords)),
        }

    @staticmethod
    def _rubric_keywords(*, subject_name: str, focus_text: str, title_text: str, snippet_text: str) -> List[List[str]]:
        focus_terms = ExamEngine._keyword_terms(focus_text)
        title_terms = ExamEngine._keyword_terms(title_text)
        snippet_terms = ExamEngine._keyword_terms(snippet_text)
        subject_terms = ExamEngine._keyword_terms(subject_name)
        common_terms = ["概念", "要点", "条件", "特征", "应用", "考点", "大纲", "题源", "易错", "结论"]
        return [
            focus_terms + ["概念", "含义", "定义", "核心"],
            focus_terms + title_terms[:4] + ["要点", "条件", "特征"],
            snippet_terms[:5] + ["题源", "材料", "考法", "应用"],
            subject_terms + common_terms,
            common_terms,
        ]

    @staticmethod
    def _keyword_terms(text: str) -> List[str]:
        cleaned = re.sub(r"[^\w\u4e00-\u9fff]+", " ", str(text or ""))
        terms = [term for term in cleaned.split() if len(term) >= 2]
        chinese_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", cleaned)
        for chunk in chinese_chunks:
            if len(chunk) <= 8:
                terms.append(chunk)
            else:
                terms.extend(chunk[index : index + 4] for index in range(0, min(len(chunk) - 1, 16), 4))
        return list(dict.fromkeys(terms))[:12]

    @staticmethod
    def _format_scoring_points(scoring_points: List[Dict[str, Any]]) -> str:
        return "；".join(
            f"{index + 1}. {point.get('label')}（{point.get('score', 0)}分）"
            for index, point in enumerate(scoring_points)
        )

    @staticmethod
    def _clean_online_text(value: str, *, limit: int, fallback: str = "") -> str:
        text = re.sub(r"\s+", " ", str(value or "")).strip()
        if not text:
            return fallback
        return text[:limit]

    def _build_online_search_keyword(self, subject: Subject, mode: str, config: Dict[str, Any]) -> str:
        terms = [str(self._resolve_exam_year(config)), "模拟题", "真题", "答案解析"]
        if config.get("chapter_ids"):
            chapters = (
                self.db.query(KnowledgePoint.name)
                .join(Chapter, KnowledgePoint.chapter_id == Chapter.id)
                .filter(Chapter.id.in_(config["chapter_ids"]))
                .limit(3)
                .all()
            )
            terms.extend(name for (name,) in chapters)
        return " ".join([subject.name, *terms])

    @staticmethod
    def _resolve_exam_year(config: Dict[str, Any]) -> int:
        raw_year = config.get("year") if config else None
        try:
            year = int(raw_year) if raw_year not in (None, "") else datetime.now().year
        except (TypeError, ValueError):
            year = datetime.now().year
        return max(2000, min(2100, year))

    @staticmethod
    def _split_online_content(raw_content: str) -> tuple[str, str]:
        lines = [line.strip() for line in raw_content.splitlines() if line.strip()]
        if not lines:
            return "线上题源", ""
        return lines[0][:120], " ".join(lines[1:])[:400]

    @staticmethod
    def _resolve_generated_chapter_id(config: Dict[str, Any]) -> Optional[int]:
        chapter_ids = config.get("chapter_ids")
        if isinstance(chapter_ids, list) and chapter_ids:
            try:
                return int(chapter_ids[0])
            except (TypeError, ValueError):
                return None
        return None

    @staticmethod
    def _normalize_positive_int(value: Any, default: int, maximum: Optional[int] = None) -> int:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            parsed = default
        parsed = max(1, parsed)
        if maximum is not None:
            parsed = min(maximum, parsed)
        return parsed

    def start_exam(self, exam_id: int, user_id: int) -> Dict[str, Any]:
        exam = self.db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise ValueError("Exam not found.")

        session_id = str(uuid.uuid4())
        start_time = datetime.now()
        end_time = start_time + timedelta(minutes=exam.duration)
        session = ExamSession(
            session_id=session_id,
            exam_id=exam_id,
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
            status=ExamStatus.IN_PROGRESS.value,
            answers={},
        )
        self.db.add(session)
        self.db.commit()

        if self.redis:
            self.redis.set(
                f"exam_session:{session_id}",
                {
                    "user_id": user_id,
                    "exam_id": exam_id,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                },
                expire=exam.duration * 60,
            )

        return {
            "session_id": session_id,
            "exam_id": exam_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration": exam.duration,
            "status": session.status,
        }

    def submit_answer(self, session_id: str, question_id: int, answer: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            return {"success": False, "message": "Exam session not found."}

        if session.status != ExamStatus.IN_PROGRESS.value:
            return {"success": False, "message": "Exam session is not active."}

        if session.end_time and datetime.now() > session.end_time:
            session.status = ExamStatus.TIMEOUT.value
            self.db.commit()
            return {"success": False, "message": "Exam session has timed out."}

        answers = dict(session.answers or {})
        answers[str(question_id)] = answer
        session.answers = answers
        self.db.commit()

        return {"success": True, "message": "Answer saved.", "answered_count": len(answers)}

    def submit_paper(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")

        score_result = self.auto_score(session_id)
        session.status = ExamStatus.COMPLETED.value
        session.score = score_result["score"]
        session.correct_count = score_result["correct_count"]
        session.total_count = score_result["total_count"]
        session.submitted_at = datetime.now()
        self.db.commit()

        self.archive_wrong_questions(session_id, session.user_id, score_result)
        self.update_user_mastery(session.user_id, score_result)
        if self.redis:
            self.redis.delete(f"exam_session:{session_id}")
        return score_result

    def auto_score(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")

        exam = self.db.query(Exam).filter(Exam.id == session.exam_id).first()
        if not exam:
            raise ValueError("Exam not found.")

        question_ids = [int(question_id) for question_id in (exam.question_ids or [])]
        questions = self.db.query(Question).filter(Question.id.in_(question_ids)).all()
        questions_by_id = {question.id: question for question in questions}

        score = 0
        correct_count = 0
        objective_count = 0
        subjective_count = 0
        auto_scored_count = 0
        wrong_questions: List[int] = []
        question_analysis: List[Dict[str, Any]] = []

        for question_id in question_ids:
            question = questions_by_id.get(question_id)
            if not question:
                continue

            user_answer = (session.answers or {}).get(str(question.id), "")
            objective = question.question_type in {
                QuestionType.SINGLE_CHOICE.value,
                QuestionType.MULTIPLE_CHOICE.value,
                QuestionType.FILL_BLANK.value,
            }
            if objective:
                objective_count += 1
                is_correct = self._check_answer(question, user_answer)
                earned_score = question.score if is_correct else 0
                grading = self._build_objective_grading(question, user_answer, is_correct, earned_score)
            else:
                subjective_count += 1
                grading = self._score_subjective_answer(question, user_answer)
                earned_score = grading["score"]
                is_correct = earned_score >= max(1, round((question.score or 0) * 0.6))

            auto_scored_count += 1
            score += earned_score
            correct_count += 1 if is_correct else 0
            if earned_score < (question.score or 0):
                wrong_questions.append(question.id)

            question_analysis.append(
                {
                    "question_id": question.id,
                    "content": question.content,
                    "question_type": question.question_type,
                    "options": question.options or [],
                    "user_answer": user_answer,
                    "correct_answer": question.answer,
                    "is_correct": is_correct,
                    "score": earned_score,
                    "full_score": question.score,
                    "explanation": self._strip_scoring_rubric(question.explanation),
                    "scoring_points": grading.get("scoring_points", []),
                    "final_explanation": grading.get("final_explanation", ""),
                    "grading_method": grading.get("grading_method", "auto"),
                }
            )

        total_count = len(question_ids)
        total_score = exam.total_score or sum(question.score or 0 for question in questions)
        return {
            "session_id": session_id,
            "score": score,
            "total_score": total_score,
            "correct_count": correct_count,
            "total_count": total_count,
            "objective_count": objective_count,
            "subjective_count": subjective_count,
            "auto_scored_count": auto_scored_count,
            "manual_count": 0,
            "accuracy": score / total_score if total_score else 0,
            "wrong_questions": wrong_questions,
            "question_analysis": question_analysis,
        }

    def archive_wrong_questions(
        self,
        session_id: str,
        user_id: int,
        score_result: Optional[Dict[str, Any]] = None,
    ) -> bool:
        score_result = score_result or self.auto_score(session_id)
        analysis = score_result.get("question_analysis", [])
        answers_by_id = {item["question_id"]: item.get("user_answer", "") for item in analysis}
        wrong_ids = set(score_result.get("wrong_questions", []))
        answered_ids = [item["question_id"] for item in analysis if item.get("is_correct") is not None]
        existing_rows = (
            self.db.query(WrongQuestion)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id.in_(answered_ids))
            .all()
            if answered_ids
            else []
        )
        existing_by_question = {row.question_id: row for row in existing_rows}

        for question_id in wrong_ids:
            existing = (
                existing_by_question.get(question_id)
                or self.db.query(WrongQuestion)
                .filter(and_(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id))
                .first()
            )
            if existing:
                existing.wrong_count = (existing.wrong_count or 0) + 1
                existing.user_answer = answers_by_id.get(question_id)
                existing.last_wrong_at = datetime.now()
                existing.is_mastered = False
            else:
                self.db.add(
                    WrongQuestion(
                        user_id=user_id,
                        question_id=question_id,
                        session_id=session_id,
                        user_answer=answers_by_id.get(question_id),
                        wrong_count=1,
                        last_wrong_at=datetime.now(),
                    )
                )

        for item in analysis:
            question_id = item["question_id"]
            if item.get("is_correct") is True and question_id in existing_by_question:
                existing_by_question[question_id].is_mastered = True
                existing_by_question[question_id].user_answer = answers_by_id.get(question_id)

        self.db.commit()
        return True

    def update_user_mastery(self, user_id: int, score_result: Dict[str, Any]) -> bool:
        analysis = [
            item
            for item in score_result.get("question_analysis", [])
            if item.get("is_correct") is not None
        ]
        if not analysis:
            return False

        question_ids = [item["question_id"] for item in analysis]
        links = (
            self.db.query(QuestionKnowledgePoint)
            .filter(QuestionKnowledgePoint.question_id.in_(question_ids))
            .all()
        )
        point_ids_by_question: Dict[int, List[int]] = defaultdict(list)
        for link in links:
            point_ids_by_question[link.question_id].append(link.knowledge_point_id)

        now = datetime.now()
        changed = False
        for item in analysis:
            point_ids = point_ids_by_question.get(item["question_id"], [])
            if not point_ids:
                continue

            for point_id in point_ids:
                mastery = (
                    self.db.query(UserMastery)
                    .filter(UserMastery.user_id == user_id, UserMastery.knowledge_point_id == point_id)
                    .first()
                )
                if not mastery:
                    mastery = UserMastery(
                        user_id=user_id,
                        knowledge_point_id=point_id,
                        mastery_level=0.0,
                        correct_count=0,
                        wrong_count=0,
                    )
                    self.db.add(mastery)

                if item["is_correct"]:
                    mastery.correct_count = (mastery.correct_count or 0) + 1
                else:
                    mastery.wrong_count = (mastery.wrong_count or 0) + 1

                attempts = max((mastery.correct_count or 0) + (mastery.wrong_count or 0), 1)
                mastery.mastery_level = round((mastery.correct_count or 0) / attempts, 2)
                mastery.last_practice_time = now
                mastery.next_review_time = self._next_review_time(now, mastery.mastery_level, bool(item["is_correct"]))
                changed = True

        if changed:
            self.db.commit()
        return changed

    def get_exam_history(self, user_id: int, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
        query = (
            self.db.query(ExamSession)
            .filter(ExamSession.user_id == user_id)
            .order_by(ExamSession.start_time.desc())
        )
        total = query.count()
        sessions = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_session(session) for session in sessions],
        }

    def get_wrong_questions(
        self,
        user_id: int,
        subject_id: Optional[int] = None,
        chapter_ids: Optional[List[int]] = None,
        is_mastered: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Dict[str, Any]:
        query = (
            self.db.query(WrongQuestion, Question)
            .join(Question, WrongQuestion.question_id == Question.id)
            .filter(WrongQuestion.user_id == user_id)
        )
        if subject_id:
            query = query.filter(Question.subject_id == subject_id)
        if chapter_ids:
            query = query.filter(Question.chapter_id.in_(chapter_ids))
        if is_mastered is not None:
            query = query.filter(WrongQuestion.is_mastered.is_(is_mastered))
        if keyword:
            pattern = f"%{keyword.strip()}%"
            query = query.filter(Question.content.ilike(pattern))

        total = query.count()
        rows = (
            query.order_by(WrongQuestion.is_mastered.asc(), WrongQuestion.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "items": [self._serialize_wrong_question(wrong, question) for wrong, question in rows],
        }

    def export_wrong_questions(
        self,
        user_id: int,
        export_format: str = "markdown",
        subject_id: Optional[int] = None,
        chapter_ids: Optional[List[int]] = None,
        is_mastered: Optional[bool] = None,
        keyword: Optional[str] = None,
    ) -> Dict[str, str]:
        export_format = export_format.lower()
        result = self.get_wrong_questions(
            user_id=user_id,
            subject_id=subject_id,
            chapter_ids=chapter_ids,
            is_mastered=is_mastered,
            keyword=keyword,
            page=1,
            page_size=1000,
        )
        items = result["items"]
        if export_format == "csv":
            return {
                "filename": f"wrong_questions_{user_id}.csv",
                "media_type": "text/csv; charset=utf-8",
                "content": self._wrong_questions_to_csv(items),
            }
        if export_format in {"word", "doc"}:
            return {
                "filename": f"wrong_questions_{user_id}.doc",
                "media_type": "application/msword; charset=utf-8",
                "content": self._wrong_questions_to_word_html(items),
            }
        return {
            "filename": f"wrong_questions_{user_id}.md",
            "media_type": "text/markdown; charset=utf-8",
            "content": self._wrong_questions_to_markdown(items),
        }

    def update_wrong_question(
        self,
        user_id: int,
        question_id: int,
        is_mastered: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        note: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        row = (
            self.db.query(WrongQuestion, Question)
            .join(Question, WrongQuestion.question_id == Question.id)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id)
            .first()
        )
        if not row:
            return None

        wrong, question = row
        if is_mastered is not None:
            wrong.is_mastered = is_mastered
        if tags is not None:
            wrong.tags = tags
        if note is not None:
            wrong.note = note
        self.db.commit()
        self.db.refresh(wrong)
        return self._serialize_wrong_question(wrong, question)

    def remove_wrong_question(self, user_id: int, question_id: int) -> bool:
        wrong = (
            self.db.query(WrongQuestion)
            .filter(WrongQuestion.user_id == user_id, WrongQuestion.question_id == question_id)
            .first()
        )
        if not wrong:
            return False
        self.db.delete(wrong)
        self.db.commit()
        return True

    @staticmethod
    def _wrong_questions_to_csv(items: List[Dict[str, Any]]) -> str:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["题目ID", "题型", "题目", "你的答案", "参考答案", "错题次数", "掌握状态", "知识点", "解析"])
        for item in items:
            question = item["question"]
            writer.writerow(
                [
                    item["question_id"],
                    question.get("question_type") or "",
                    question.get("content") or "",
                    item.get("user_answer") or "",
                    question.get("answer") or "",
                    item.get("wrong_count") or 0,
                    "已掌握" if item.get("is_mastered") else "未掌握",
                    "、".join(point["name"] for point in item.get("knowledge_points") or []),
                    question.get("explanation") or "",
                ]
            )
        return "\ufeff" + output.getvalue()

    @staticmethod
    def _wrong_questions_to_markdown(items: List[Dict[str, Any]]) -> str:
        lines = ["# 错题本导出", ""]
        if not items:
            lines.append("暂无错题。")
            return "\n".join(lines)

        for index, item in enumerate(items, start=1):
            question = item["question"]
            points = "、".join(point["name"] for point in item.get("knowledge_points") or []) or "未标注"
            lines.extend(
                [
                    f"## {index}. 题目 {item['question_id']}",
                    "",
                    f"- 题型：{question.get('question_type') or '-'}",
                    f"- 状态：{'已掌握' if item.get('is_mastered') else '未掌握'}",
                    f"- 错误次数：{item.get('wrong_count') or 0}",
                    f"- 知识点：{points}",
                    "",
                    str(question.get("content") or ""),
                    "",
                ]
            )
            options = question.get("options") or []
            for option_index, option in enumerate(options):
                lines.append(f"{chr(65 + option_index)}. {option}")
            if options:
                lines.append("")
            lines.extend(
                [
                    f"你的答案：{item.get('user_answer') or '-'}",
                    f"参考答案：{question.get('answer') or '-'}",
                    "",
                    f"解析：{question.get('explanation') or '-'}",
                    "",
                ]
            )
        return "\n".join(lines)

    @staticmethod
    def _wrong_questions_to_word_html(items: List[Dict[str, Any]]) -> str:
        rows = []
        for index, item in enumerate(items, start=1):
            question = item["question"]
            points = "、".join(point["name"] for point in item.get("knowledge_points") or []) or "未标注"
            rows.append(
                "<tr>"
                f"<td>{index}</td>"
                f"<td>{html.escape(str(question.get('content') or ''))}</td>"
                f"<td>{html.escape(str(item.get('user_answer') or '-'))}</td>"
                f"<td>{html.escape(str(question.get('answer') or '-'))}</td>"
                f"<td>{html.escape(points)}</td>"
                f"<td>{html.escape(str(question.get('explanation') or '-'))}</td>"
                "</tr>"
            )
        return (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<style>body{font-family:Arial,'Microsoft YaHei',sans-serif;}"
            "table{border-collapse:collapse;width:100%;}td,th{border:1px solid #ccc;padding:8px;vertical-align:top;}"
            "th{background:#f3f4f6;}</style></head><body>"
            "<h1>错题本导出</h1>"
            "<table><thead><tr><th>#</th><th>题目</th><th>你的答案</th><th>参考答案</th><th>知识点</th><th>解析</th></tr></thead>"
            f"<tbody>{''.join(rows) if rows else '<tr><td colspan=\"6\">暂无错题</td></tr>'}</tbody></table>"
            "</body></html>"
        )

    def get_session_detail(self, session_id: str) -> Dict[str, Any]:
        session = self._get_session(session_id)
        if not session:
            raise ValueError("Exam session not found.")
        return self._serialize_session(session)

    @staticmethod
    def _build_exam_name(mode: str, config: Dict[str, Any]) -> str:
        labels = {
            ExamMode.REAL_EXAM.value: "Past paper",
            ExamMode.RANDOM.value: "Random paper",
            ExamMode.CHAPTER.value: "Chapter practice",
            ExamMode.WRONG_QUESTIONS.value: "Wrong question retry",
        }
        suffix = f" {config['year']}" if config.get("year") else ""
        return f"{labels.get(mode, 'Exam')}{suffix}"

    @staticmethod
    def _serialize_exam_question(question: Question, include_answer: bool) -> Dict[str, Any]:
        data: Dict[str, Any] = {
            "id": question.id,
            "content": question.content,
            "question_type": question.question_type,
            "options": question.options or [],
            "score": question.score,
            "difficulty": question.difficulty,
            "year": question.year,
            "month": question.month,
            "chapter_id": question.chapter_id,
        }
        if include_answer:
            data["answer"] = question.answer
            data["explanation"] = ExamEngine._strip_scoring_rubric(question.explanation)
        return data

    def _serialize_wrong_question(self, wrong: WrongQuestion, question: Question) -> Dict[str, Any]:
        return {
            "id": wrong.id,
            "user_id": wrong.user_id,
            "question_id": wrong.question_id,
            "session_id": wrong.session_id,
            "user_answer": wrong.user_answer,
            "wrong_count": wrong.wrong_count,
            "is_mastered": wrong.is_mastered,
            "tags": wrong.tags or [],
            "note": wrong.note,
            "last_wrong_at": wrong.last_wrong_at.isoformat() if wrong.last_wrong_at else None,
            "created_at": wrong.created_at.isoformat() if wrong.created_at else None,
            "question": self._serialize_exam_question(question, include_answer=True),
            "knowledge_points": self._get_question_points(question.id),
        }

    def _get_question_points(self, question_id: int) -> List[Dict[str, Any]]:
        points = (
            self.db.query(KnowledgePoint)
            .join(QuestionKnowledgePoint, KnowledgePoint.id == QuestionKnowledgePoint.knowledge_point_id)
            .filter(QuestionKnowledgePoint.question_id == question_id)
            .all()
        )
        return [
            {
                "id": point.id,
                "name": point.name,
                "chapter_id": point.chapter_id,
                "importance": point.importance,
                "frequency": point.frequency,
            }
            for point in points
        ]

    def _build_objective_grading(
        self,
        question: Question,
        user_answer: str,
        is_correct: bool,
        earned_score: int,
    ) -> Dict[str, Any]:
        full_score = question.score or 0
        rubric = self._extract_scoring_rubric(question.explanation)
        scoring_points = rubric.get("scoring_points") or [
            self._scoring_point("答案与标准答案一致", full_score, [question.answer or ""])
        ]
        rendered_points = []
        for point in scoring_points:
            rendered_points.append(
                {
                    "label": point.get("label", "客观题判分"),
                    "score": int(point.get("score") or full_score),
                    "earned_score": earned_score if is_correct else 0,
                    "matched_keywords": [question.answer] if is_correct else [],
                    "missing_keywords": [] if is_correct else [question.answer],
                    "comment": "答案正确，获得本题全部分值。" if is_correct else "答案与标准答案不一致，本题不得分。",
                }
            )
        return {
            "score": earned_score,
            "scoring_points": rendered_points,
            "final_explanation": (
                f"自动判分：你的答案为“{user_answer or '-'}”，标准答案为“{question.answer}”，"
                f"{'答案正确' if is_correct else '答案不正确'}，本题得 {earned_score}/{full_score} 分。"
            ),
            "grading_method": "objective_auto",
        }

    def _score_subjective_answer(self, question: Question, user_answer: str) -> Dict[str, Any]:
        full_score = question.score or 0
        answer_text = str(user_answer or "").strip()
        rubric = self._extract_scoring_rubric(question.explanation)
        scoring_points = rubric.get("scoring_points") or self._fallback_scoring_points(question)
        if not answer_text:
            rendered_empty = [
                {
                    "label": point.get("label", "评分项"),
                    "score": int(point.get("score") or 0),
                    "earned_score": 0,
                    "matched_keywords": [],
                    "missing_keywords": point.get("keywords", [])[:5],
                    "comment": "未作答，该评分项不得分。",
                }
                for point in scoring_points
            ]
            return {
                "score": 0,
                "scoring_points": rendered_empty,
                "final_explanation": f"自动评分：未检测到作答内容，本题得 0/{full_score} 分。",
                "grading_method": "rubric_auto",
            }

        ai_result = self._score_subjective_answer_with_ai(
            question=question,
            user_answer=answer_text,
            scoring_points=scoring_points,
            full_score=full_score,
        )
        if ai_result:
            return ai_result

        normalized_answer = self._normalize_subjective_text(answer_text)
        answer_length = len(normalized_answer)
        rendered_points = []
        earned_total = 0

        for point in scoring_points:
            point_score = int(point.get("score") or 0)
            keywords = [str(keyword) for keyword in point.get("keywords", []) if str(keyword or "").strip()]
            matched_keywords = [
                keyword
                for keyword in keywords
                if self._normalize_subjective_text(keyword) in normalized_answer
            ]
            structural_hits = self._subjective_structure_hits(normalized_answer, point.get("label", ""))
            earned = self._score_rubric_point(
                point_score=point_score,
                keyword_count=len(keywords),
                matched_count=len(matched_keywords),
                structural_hits=structural_hits,
                answer_length=answer_length,
            )
            earned_total += earned
            missing_keywords = [keyword for keyword in keywords if keyword not in matched_keywords][:5]
            rendered_points.append(
                {
                    "label": point.get("label", "评分项"),
                    "score": point_score,
                    "earned_score": earned,
                    "matched_keywords": matched_keywords[:8],
                    "missing_keywords": missing_keywords,
                    "comment": self._rubric_point_comment(earned, point_score, matched_keywords, structural_hits),
                }
            )

        earned_total = max(0, min(full_score, int(round(earned_total))))
        coverage = earned_total / full_score if full_score else 0
        if coverage >= 0.85:
            level = "要点覆盖充分"
        elif coverage >= 0.6:
            level = "主要要点基本覆盖"
        elif coverage > 0:
            level = "只覆盖了部分要点"
        else:
            level = "未命中有效评分点"
        return {
            "score": earned_total,
            "scoring_points": rendered_points,
            "final_explanation": f"自动评分：{level}，本题得 {earned_total}/{full_score} 分。建议对照评分项补全概念、依据、分析和结论。",
            "grading_method": "rubric_auto",
        }

    def _score_subjective_answer_with_ai(
        self,
        *,
        question: Question,
        user_answer: str,
        scoring_points: List[Dict[str, Any]],
        full_score: int,
    ) -> Optional[Dict[str, Any]]:
        if not settings.UNITY2_API_KEY or OpenAI is None:
            return None

        try:
            client = OpenAI(
                api_key=settings.UNITY2_API_KEY,
                base_url=settings.UNITY2_BASE_URL,
                timeout=12,
            )
            response = client.chat.completions.create(
                model=settings.UNITY2_MODEL,
                temperature=0,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "你是自学考试阅卷老师。请严格依据给定评分项评分，只返回 JSON。"
                            "JSON 结构：{\"score\":数字,\"final_explanation\":\"中文解释\","
                            "\"scoring_points\":[{\"label\":\"评分项\",\"score\":满分,"
                            "\"earned_score\":得分,\"matched_keywords\":[\"命中\"],"
                            "\"missing_keywords\":[\"缺失\"],\"comment\":\"说明\"}]}"
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question.content,
                                "reference_answer": question.answer,
                                "full_score": full_score,
                                "scoring_points": scoring_points,
                                "user_answer": user_answer,
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
            )
            content = response.choices[0].message.content if response.choices else ""
            parsed = json.loads(content or "{}")
        except Exception:
            return None

        if not isinstance(parsed, dict):
            return None
        try:
            earned_score = int(round(float(parsed.get("score", 0))))
        except (TypeError, ValueError):
            return None
        earned_score = max(0, min(full_score, earned_score))
        rendered_points = self._normalize_ai_scoring_points(
            parsed.get("scoring_points"),
            scoring_points,
            full_score,
        )
        return {
            "score": earned_score,
            "scoring_points": rendered_points,
            "final_explanation": str(parsed.get("final_explanation") or f"AI 自动评分完成，本题得 {earned_score}/{full_score} 分。"),
            "grading_method": "ai_rubric_auto",
        }

    @staticmethod
    def _normalize_ai_scoring_points(
        ai_points: Any,
        fallback_points: List[Dict[str, Any]],
        full_score: int,
    ) -> List[Dict[str, Any]]:
        if not isinstance(ai_points, list) or not ai_points:
            return [
                {
                    "label": point.get("label", "评分项"),
                    "score": int(point.get("score") or 0),
                    "earned_score": 0,
                    "matched_keywords": [],
                    "missing_keywords": point.get("keywords", [])[:5],
                    "comment": "AI 未返回该项明细，按备用评分项展示。",
                }
                for point in fallback_points
            ]

        normalized = []
        for index, item in enumerate(ai_points):
            if not isinstance(item, dict):
                continue
            fallback = fallback_points[index] if index < len(fallback_points) else {}
            point_score = int(item.get("score") or fallback.get("score") or 0)
            try:
                earned = int(round(float(item.get("earned_score", 0))))
            except (TypeError, ValueError):
                earned = 0
            normalized.append(
                {
                    "label": str(item.get("label") or fallback.get("label") or "评分项"),
                    "score": point_score,
                    "earned_score": max(0, min(point_score or full_score, earned)),
                    "matched_keywords": item.get("matched_keywords") if isinstance(item.get("matched_keywords"), list) else [],
                    "missing_keywords": item.get("missing_keywords") if isinstance(item.get("missing_keywords"), list) else [],
                    "comment": str(item.get("comment") or ""),
                }
            )
        return normalized

    @classmethod
    def _extract_scoring_rubric(cls, explanation: Optional[str]) -> Dict[str, Any]:
        if not explanation:
            return {}
        match = cls.SCORING_RUBRIC_PATTERN.search(explanation)
        if not match:
            return {}
        try:
            data = json.loads(match.group(1))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {}
        return data if isinstance(data, dict) else {}

    @classmethod
    def _strip_scoring_rubric(cls, explanation: Optional[str]) -> str:
        if not explanation:
            return ""
        return cls.SCORING_RUBRIC_PATTERN.sub("", explanation).strip()

    @staticmethod
    def _fallback_scoring_points(question: Question) -> List[Dict[str, Any]]:
        full_score = question.score or 0
        answer_terms = ExamEngine._keyword_terms(question.answer or question.content)
        if not answer_terms:
            answer_terms = ["概念", "要点", "应用", "结论"]
        split_scores = ExamEngine._split_score(full_score, 4)
        labels = ["核心概念", "关键要点", "结合材料或应用", "表达结构"]
        return [
            ExamEngine._scoring_point(label, score, answer_terms[index::4] + ["概念", "要点", "应用", "结论"])
            for index, (label, score) in enumerate(zip(labels, split_scores))
        ]

    @staticmethod
    def _split_score(total_score: int, parts: int) -> List[int]:
        base = total_score // parts if parts else total_score
        scores = [base for _ in range(parts)]
        for index in range(total_score - base * parts):
            scores[index] += 1
        return scores

    @staticmethod
    def _normalize_subjective_text(value: str) -> str:
        return re.sub(r"\s+", "", str(value or "").upper())

    @staticmethod
    def _subjective_structure_hits(normalized_answer: str, label: str) -> int:
        indicators = ["首先", "其次", "再次", "最后", "第一", "第二", "第三", "原因", "表现", "影响", "对策", "结论", "定义", "特征", "条件", "应用"]
        hits = sum(1 for item in indicators if item in normalized_answer)
        label_terms = ExamEngine._keyword_terms(label)
        hits += sum(1 for term in label_terms if ExamEngine._normalize_subjective_text(term) in normalized_answer)
        return hits

    @staticmethod
    def _score_rubric_point(
        *,
        point_score: int,
        keyword_count: int,
        matched_count: int,
        structural_hits: int,
        answer_length: int,
    ) -> int:
        if point_score <= 0:
            return 0
        required_matches = min(2, max(1, keyword_count // 4)) if keyword_count else 1
        if matched_count >= required_matches and (answer_length >= 18 or structural_hits > 0):
            return point_score
        if matched_count > 0:
            ratio = 0.65 if answer_length >= 18 else 0.45
            return max(1, int(round(point_score * ratio)))
        if structural_hits >= 2 and answer_length >= 40:
            return max(1, int(round(point_score * 0.4)))
        if answer_length >= 80:
            return max(0, int(round(point_score * 0.25)))
        return 0

    @staticmethod
    def _rubric_point_comment(
        earned: int,
        point_score: int,
        matched_keywords: List[str],
        structural_hits: int,
    ) -> str:
        if earned >= point_score:
            return "命中该评分项的核心关键词，表达基本完整。"
        if earned > 0:
            return "部分命中该评分项，但关键词或论证层次仍不完整。"
        if structural_hits:
            return "有一定答题结构，但未命中该评分项的关键内容。"
        return "未检测到该评分项的关键内容。"

    @staticmethod
    def _check_answer(question: Question, user_answer: str) -> bool:
        correct_answer = (question.answer or "").strip().upper()
        normalized_user_answer = (user_answer or "").strip().upper()
        if question.question_type == QuestionType.MULTIPLE_CHOICE.value:
            correct_letters = set(re.sub(r"[^A-Z]", "", correct_answer))
            user_letters = set(re.sub(r"[^A-Z]", "", normalized_user_answer))
            return bool(correct_letters) and correct_letters == user_letters
        if question.question_type == QuestionType.FILL_BLANK.value:
            alternatives = [
                ExamEngine._normalize_text_answer(item)
                for item in re.split(r"[|/;；、]", question.answer or "")
                if item.strip()
            ]
            user_value = ExamEngine._normalize_text_answer(user_answer)
            return user_value in alternatives if alternatives else user_value == ExamEngine._normalize_text_answer(correct_answer)
        return ExamEngine._normalize_text_answer(correct_answer) == ExamEngine._normalize_text_answer(normalized_user_answer)

    @staticmethod
    def _normalize_text_answer(value: str) -> str:
        return re.sub(r"\s+", "", str(value or "").strip().upper())

    @staticmethod
    def _next_review_time(base_time: datetime, mastery_level: float, was_correct: bool) -> datetime:
        if not was_correct:
            return base_time + timedelta(days=1)
        if mastery_level >= 0.85:
            return base_time + timedelta(days=14)
        if mastery_level >= 0.65:
            return base_time + timedelta(days=7)
        return base_time + timedelta(days=3)

    def _get_session(self, session_id: str) -> Optional[ExamSession]:
        return self.db.query(ExamSession).filter(ExamSession.session_id == session_id).first()

    @staticmethod
    def _serialize_session(session: ExamSession) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "exam_id": session.exam_id,
            "user_id": session.user_id,
            "status": session.status,
            "answers": session.answers or {},
            "score": session.score,
            "correct_count": session.correct_count,
            "total_count": session.total_count,
            "start_time": session.start_time.isoformat() if session.start_time else None,
            "end_time": session.end_time.isoformat() if session.end_time else None,
            "submitted_at": session.submitted_at.isoformat() if session.submitted_at else None,
        }
