# -*- coding: utf-8 -*-
"""Add flashcards table.

Revision ID: 20260822_01_flashcards
Revises: 20260717_01_runtime_integrity
Create Date: 2026-08-22
"""
from alembic import op
import sqlalchemy as sa


revision = '20260822_01_flashcards'
down_revision = '20260717_01'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'flashcards',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=False, index=True),
        sa.Column('knowledge_point_id', sa.Integer(), sa.ForeignKey('knowledge_points.id'), index=True),
        sa.Column('question_id', sa.Integer(), sa.ForeignKey('questions.id'), index=True),
        sa.Column('front', sa.Text(), nullable=False),
        sa.Column('back', sa.Text(), nullable=False),
        sa.Column('card_type', sa.String(20), nullable=False, server_default='auto'),
        sa.Column('tags', sa.String(500)),
        sa.Column('ease_factor', sa.Float(), nullable=False, server_default='2.5'),
        sa.Column('interval_days', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('repetitions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_review', sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column('last_review', sa.DateTime(timezone=True)),
        sa.Column('is_suspended', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True)),
    )


def downgrade() -> None:
    op.drop_table('flashcards')
