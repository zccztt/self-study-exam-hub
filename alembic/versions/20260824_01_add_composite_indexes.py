"""Add composite indexes for query performance.

Revision ID: 20260824_01
Revises: 20260822_01
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_01"
down_revision = "20260822_01_flashcards"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # WrongQuestion: composite index on (user_id, is_mastered, last_wrong_at)
    op.create_index(
        "ix_wrong_questions_user_mastered_time",
        "wrong_questions",
        ["user_id", "is_mastered", "last_wrong_at"],
    )

    # ExamSession: composite index on (user_id, status)
    op.create_index(
        "ix_exam_sessions_user_status",
        "exam_sessions",
        ["user_id", "status"],
    )

    # DailyTask: composite index on (user_id, task_date)
    op.create_index(
        "ix_daily_tasks_user_date",
        "daily_tasks",
        ["user_id", "task_date"],
    )

    # UserMastery: composite index on (user_id, knowledge_point_id)
    op.create_index(
        "ix_user_mastery_user_point",
        "user_mastery",
        ["user_id", "knowledge_point_id"],
    )

    # UserMastery: composite index on (user_id, mastery_level)
    op.create_index(
        "ix_user_mastery_user_level",
        "user_mastery",
        ["user_id", "mastery_level"],
    )


def downgrade() -> None:
    op.drop_index("ix_user_mastery_user_level", table_name="user_mastery")
    op.drop_index("ix_user_mastery_user_point", table_name="user_mastery")
    op.drop_index("ix_daily_tasks_user_date", table_name="daily_tasks")
    op.drop_index("ix_exam_sessions_user_status", table_name="exam_sessions")
    op.drop_index("ix_wrong_questions_user_mastered_time", table_name="wrong_questions")
