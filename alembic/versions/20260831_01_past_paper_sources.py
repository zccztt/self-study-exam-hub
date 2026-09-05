# -*- coding: utf-8 -*-
"""Store raw PDF/image/video links and ingestion results."""

from alembic import op
import sqlalchemy as sa

revision = "20260831_01_past_paper_sources"
down_revision = "20260825_01_crawl_logs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "past_paper_sources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("subject_id", sa.Integer(), sa.ForeignKey("subjects.id"), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("month", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("url", sa.String(length=1000), nullable=False),
        sa.Column("source", sa.String(length=100), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False, server_default="html"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="pending"),
        sa.Column("local_path", sa.String(length=500), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("parsed_question_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("linked_paper_id", sa.Integer(), sa.ForeignKey("past_papers.id"), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("url", name="uq_past_paper_sources_url"),
    )
    op.create_index("ix_past_paper_sources_subject_id", "past_paper_sources", ["subject_id"])
    op.create_index("ix_past_paper_sources_year", "past_paper_sources", ["year"])
    op.create_index("ix_past_paper_sources_month", "past_paper_sources", ["month"])
    op.create_index("ix_past_paper_sources_source", "past_paper_sources", ["source"])


def downgrade() -> None:
    op.drop_table("past_paper_sources")
