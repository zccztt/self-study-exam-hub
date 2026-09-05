"""Add user_context to study_plans table.

Revision ID: 20260904_01_user_context
Revises: 20260825_01_crawl_logs
Create Date: 2026-09-04
"""
from alembic import op
import sqlalchemy as sa

revision = '20260904_01_user_context'
down_revision = '20260825_01_crawl_logs'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('study_plans', sa.Column('user_context', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('study_plans', 'user_context')
