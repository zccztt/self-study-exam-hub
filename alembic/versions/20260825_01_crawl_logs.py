"""Add crawl_logs table.

Revision ID: 20260825_01_crawl_logs
Revises: 20260824_02_enrollment
Create Date: 2026-08-25
"""
from alembic import op
import sqlalchemy as sa

revision = '20260825_01_crawl_logs'
down_revision = '20260824_02_enrollment'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'crawl_logs',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('source', sa.String(50), nullable=False),
        sa.Column('province_code', sa.String(10), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='running'),
        sa.Column('schools_found', sa.Integer(), server_default=sa.text('0')),
        sa.Column('majors_found', sa.Integer(), server_default=sa.text('0')),
        sa.Column('majors_created', sa.Integer(), server_default=sa.text('0')),
        sa.Column('majors_updated', sa.Integer(), server_default=sa.text('0')),
        sa.Column('courses_found', sa.Integer(), server_default=sa.text('0')),
        sa.Column('links_created', sa.Integer(), server_default=sa.text('0')),
        sa.Column('error_count', sa.Integer(), server_default=sa.text('0')),
        sa.Column('errors', sa.JSON(), nullable=True),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_crawl_logs_source', 'crawl_logs', ['source'])
    op.create_index('ix_crawl_logs_province_code', 'crawl_logs', ['province_code'])


def downgrade() -> None:
    op.drop_table('crawl_logs')
