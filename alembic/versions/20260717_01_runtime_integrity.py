"""Add runtime integrity tables and unique indexes.

Revision ID: 20260717_01
Revises:
"""

from alembic import op
import sqlalchemy as sa

from backend.models import Base


revision = "20260717_01"
down_revision = None
branch_labels = None
depends_on = None


UNIQUE_INDEXES = {
    "wrong_questions": ("uq_wrong_questions_user_question", ["user_id", "question_id"]),
    "question_favorites": ("uq_question_favorites_user_question", ["user_id", "question_id"]),
    "video_favorites": ("uq_video_favorites_user_video", ["user_id", "video_id"]),
    "daily_tasks": ("uq_daily_tasks_plan_date_subject", ["plan_id", "task_date", "subject_id"]),
}


def upgrade() -> None:
    bind = op.get_bind()
    # Establish the complete baseline before applying legacy runtime indexes.
    Base.metadata.create_all(bind=bind, checkfirst=True)
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "exam_results" not in tables:
        op.create_table(
            "exam_results",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("session_id", sa.String(length=100), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True)),
            sa.ForeignKeyConstraint(["session_id"], ["exam_sessions.session_id"]),
            sa.UniqueConstraint("session_id", name="uq_exam_results_session_id"),
        )

    inspector = sa.inspect(bind)
    for table, (name, columns) in UNIQUE_INDEXES.items():
        if table not in tables:
            continue
        existing = {item["name"] for item in inspector.get_indexes(table)}
        existing.update(item["name"] for item in inspector.get_unique_constraints(table))
        if name not in existing:
            op.create_index(name, table, columns, unique=True)


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    for table, (name, _) in reversed(list(UNIQUE_INDEXES.items())):
        if table in tables and name in {item["name"] for item in inspector.get_indexes(table)}:
            op.drop_index(name, table_name=table)
    if "exam_results" in tables:
        op.drop_table("exam_results")
