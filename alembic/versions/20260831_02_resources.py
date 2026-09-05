# -*- coding: utf-8 -*-
"""Add resources table and junction tables for question/paper-source attachments."""

from alembic import op
import sqlalchemy as sa

revision = "20260831_02_resources"
down_revision = "20260831_01_past_paper_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- resources 主表 ----
    op.create_table(
        "resources",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=20), nullable=False),
        sa.Column("storage_type", sa.String(length=20), nullable=False),
        sa.Column("minio_object", sa.String(length=500), nullable=True),
        sa.Column("external_url", sa.String(length=1000), nullable=True),
        sa.Column("content_type", sa.String(length=100), nullable=True),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("file_hash", sa.String(length=64), nullable=True),
        sa.Column("content_text", sa.Text(), nullable=True),
        sa.Column("ocr_status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("thumbnail_object", sa.String(length=500), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_resources_media_type", "resources", ["media_type"])
    op.create_index("ix_resources_file_hash", "resources", ["file_hash"])

    # ---- question_resources 关联表 ----
    op.create_table(
        "question_resources",
        sa.Column(
            "question_id", sa.Integer(),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "resource_id", sa.Integer(),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    # ---- paper_source_resources 关联表 ----
    op.create_table(
        "paper_source_resources",
        sa.Column(
            "paper_source_id", sa.Integer(),
            sa.ForeignKey("past_paper_sources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "resource_id", sa.Integer(),
            sa.ForeignKey("resources.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    op.drop_table("paper_source_resources")
    op.drop_table("question_resources")
    op.drop_table("resources")
