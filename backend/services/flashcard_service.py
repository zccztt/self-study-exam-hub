# -*- coding: utf-8 -*-
"""Flashcard service: generation, SM-2 scheduling, and review."""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import func as sa_func
from sqlalchemy.orm import Session

from backend.models.chapter import Chapter, KnowledgePoint, QuestionKnowledgePoint
from backend.models.flashcard import Flashcard
from backend.models.question import Question, QuestionType
from backend.models.subject import Subject


class FlashcardService:
    """Flashcard generation and SM-2 spaced repetition scheduling."""

    # Maximum cards to auto-generate per subject in one call
    MAX_AUTO_GENERATE = 200

    def __init__(self, db: Session):
        self.db = db

    def generate_cards_for_subject(self, user_id: int, subject_id: int) -> Dict[str, Any]:
        """Auto-generate flashcards from knowledge points and choice questions."""
        now = datetime.now(timezone.utc)
        created_count = 0
        skipped_count = 0

        # Find existing cards to avoid duplicates
        existing_kp_ids = set(
            row[0]
            for row in self.db.query(Flashcard.knowledge_point_id)
            .filter(
                Flashcard.user_id == user_id,
                Flashcard.subject_id == subject_id,
                Flashcard.knowledge_point_id.isnot(None),
                Flashcard.question_id.is_(None),
            )
            .all()
        )
        existing_q_ids = set(
            row[0]
            for row in self.db.query(Flashcard.question_id)
            .filter(
                Flashcard.user_id == user_id,
                Flashcard.subject_id == subject_id,
                Flashcard.question_id.isnot(None),
            )
            .all()
        )

        # 1. Generate concept cards from knowledge points
        chapters = self.db.query(Chapter).filter(Chapter.subject_id == subject_id).all()
        chapter_ids = [ch.id for ch in chapters]

        if chapter_ids:
            knowledge_points = (
                self.db.query(KnowledgePoint)
                .filter(KnowledgePoint.chapter_id.in_(chapter_ids))
                .order_by(KnowledgePoint.frequency.desc())
                .limit(self.MAX_AUTO_GENERATE)
                .all()
            )

            for kp in knowledge_points:
                if kp.id in existing_kp_ids:
                    skipped_count += 1
                    continue
                if not kp.description:
                    continue

                card = Flashcard(
                    user_id=user_id,
                    subject_id=subject_id,
                    knowledge_point_id=kp.id,
                    front=f"什么是{kp.name}？",
                    back=kp.description,
                    card_type="auto",
                    next_review=now,
                )
                self.db.add(card)
                created_count += 1

        # 2. Generate question cards from single-choice questions
        choice_questions = (
            self.db.query(Question)
            .filter(
                Question.subject_id == subject_id,
                Question.question_type == QuestionType.SINGLE_CHOICE.value,
                Question.explanation.isnot(None),
            )
            .order_by(Question.frequency.desc())
            .limit(self.MAX_AUTO_GENERATE)
            .all()
        )

        for q in choice_questions:
            if q.id in existing_q_ids:
                skipped_count += 1
                continue
            if created_count >= self.MAX_AUTO_GENERATE:
                break

            # Build back side: correct answer + explanation
            answer_text = f"答案：{q.answer}"
            if q.explanation:
                answer_text += f"\n\n解析：{q.explanation}"

            card = Flashcard(
                user_id=user_id,
                subject_id=subject_id,
                question_id=q.id,
                front=q.content,
                back=answer_text,
                card_type="auto",
                next_review=now,
            )
            self.db.add(card)
            created_count += 1

        self.db.commit()
        return {
            "created_count": created_count,
            "skipped_count": skipped_count,
            "message": f"已生成 {created_count} 张闪卡，跳过 {skipped_count} 张已存在卡片。",
        }

    def get_due_cards(
        self,
        user_id: int,
        subject_id: Optional[int] = None,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """Get cards due for review today."""
        now = datetime.now(timezone.utc)
        query = self.db.query(Flashcard).filter(
            Flashcard.user_id == user_id,
            Flashcard.is_suspended.is_(False),
            Flashcard.next_review <= now,
        )
        if subject_id:
            query = query.filter(Flashcard.subject_id == subject_id)

        total_due = query.count()
        cards = query.order_by(Flashcard.next_review.asc()).limit(limit).all()

        return {
            "total_due": total_due,
            "items": [
                {
                    "id": card.id,
                    "front": card.front,
                    "back": card.back,
                    "card_type": card.card_type,
                    "tags": card.tags,
                    "ease_factor": card.ease_factor,
                    "interval_days": card.interval_days,
                    "repetitions": card.repetitions,
                    "subject_id": card.subject_id,
                    "knowledge_point_id": card.knowledge_point_id,
                    "question_id": card.question_id,
                }
                for card in cards
            ],
        }

    def review_card(self, card_id: int, user_id: int, quality: int) -> Dict[str, Any]:
        """
        Apply SM-2 algorithm to update card scheduling.

        quality: 0-5
            0 = completely forgotten
            1 = wrong, but recognized after seeing answer
            2 = wrong, but answer felt familiar
            3 = correct with serious difficulty
            4 = correct with some hesitation
            5 = perfect, effortless recall
        """
        card = self.db.query(Flashcard).filter_by(id=card_id, user_id=user_id).first()
        if not card:
            raise ValueError("卡片不存在")

        quality = max(0, min(5, quality))
        now = datetime.now(timezone.utc)
        card.last_review = now

        if quality >= 3:  # Correct response
            card.repetitions += 1
            if card.repetitions == 1:
                card.interval_days = 1
            elif card.repetitions == 2:
                card.interval_days = 3
            else:
                card.interval_days = round(card.interval_days * card.ease_factor)
        else:  # Incorrect - reset
            card.repetitions = 0
            card.interval_days = 1

        # Update ease factor (SM-2 formula)
        card.ease_factor = max(
            1.3,
            card.ease_factor + 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02),
        )
        card.next_review = now + timedelta(days=card.interval_days)

        self.db.commit()
        return {
            "card_id": card.id,
            "next_review": card.next_review.isoformat(),
            "interval_days": card.interval_days,
            "ease_factor": round(card.ease_factor, 2),
            "repetitions": card.repetitions,
        }

    def get_stats(self, user_id: int, subject_id: Optional[int] = None) -> Dict[str, Any]:
        """Get flashcard statistics for a user."""
        now = datetime.now(timezone.utc)
        base_query = self.db.query(Flashcard).filter(
            Flashcard.user_id == user_id,
            Flashcard.is_suspended.is_(False),
        )
        if subject_id:
            base_query = base_query.filter(Flashcard.subject_id == subject_id)

        total = base_query.count()
        due_today = base_query.filter(Flashcard.next_review <= now).count()
        mastered = base_query.filter(Flashcard.interval_days >= 21).count()
        learning = total - mastered

        return {
            "total": total,
            "due_today": due_today,
            "mastered": mastered,
            "learning": learning,
        }

    def create_custom_card(
        self,
        user_id: int,
        subject_id: int,
        front: str,
        back: str,
        tags: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a user-defined flashcard."""
        now = datetime.now(timezone.utc)
        card = Flashcard(
            user_id=user_id,
            subject_id=subject_id,
            front=front,
            back=back,
            card_type="custom",
            tags=tags,
            next_review=now,
        )
        self.db.add(card)
        self.db.commit()
        self.db.refresh(card)
        return {
            "id": card.id,
            "front": card.front,
            "back": card.back,
            "card_type": card.card_type,
            "tags": card.tags,
        }

    def suspend_card(self, card_id: int, user_id: int, suspend: bool = True) -> bool:
        """Suspend or unsuspend a card."""
        card = self.db.query(Flashcard).filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return False
        card.is_suspended = suspend
        self.db.commit()
        return True

    def delete_card(self, card_id: int, user_id: int) -> bool:
        """Delete a flashcard."""
        card = self.db.query(Flashcard).filter_by(id=card_id, user_id=user_id).first()
        if not card:
            return False
        self.db.delete(card)
        self.db.commit()
        return True
