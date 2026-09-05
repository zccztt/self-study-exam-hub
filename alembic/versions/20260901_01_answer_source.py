# -*- coding: utf-8 -*-
"""Add answer_source column to questions for answer quality tracking."""

from alembic import op
import sqlalchemy as sa

revision = "20260901_01_answer_source"
down_revision = "20260831_02_resources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "questions",
        sa.Column("answer_source", sa.String(length=20), nullable=True),
    )
    op.create_index("ix_questions_answer_source", "questions", ["answer_source"])

    # 回填：答案为占位值的标记 pending，其余标记 crawled
    op.execute(
        "UPDATE questions SET answer_source = 'pending' "
        "WHERE answer = '待核实' OR answer IS NULL OR trim(answer) = ''"
    )
    op.execute(
        "UPDATE questions SET answer_source = 'crawled' "
        "WHERE answer_source IS NULL"
    )


def downgrade() -> None:
    op.drop_index("ix_questions_answer_source", table_name="questions")
    op.drop_column("questions", "answer_source")
