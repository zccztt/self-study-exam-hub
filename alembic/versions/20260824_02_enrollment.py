"""Add enrollment models (provinces, schools, majors, user_enrollments, user_subject_status)

Revision ID: 20260824_02
Revises: 20260824_01_add_composite_indexes
Create Date: 2026-08-24
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '20260824_02_enrollment'
down_revision = ('20260824_01', 'add_source_url_001')
branch_labels = None
depends_on = None


def upgrade() -> None:
    # provinces
    op.create_table(
        'provinces',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(10), nullable=False, unique=True),
        sa.Column('name', sa.String(50), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_provinces_code', 'provinces', ['code'])

    # schools
    op.create_table(
        'schools',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('province_id', sa.Integer(), sa.ForeignKey('provinces.id'), nullable=False),
        sa.Column('code', sa.String(20), nullable=True),
        sa.Column('logo_url', sa.String(500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_schools_province_id', 'schools', ['province_id'])

    # majors
    op.create_table(
        'majors',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('code', sa.String(20), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('level', sa.String(20), nullable=False),
        sa.Column('province_id', sa.Integer(), sa.ForeignKey('provinces.id'), nullable=False),
        sa.Column('school_id', sa.Integer(), sa.ForeignKey('schools.id'), nullable=False),
        sa.Column('total_credits', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_majors_code', 'majors', ['code'])
    op.create_index('ix_majors_province_school', 'majors', ['province_id', 'school_id'])

    # major_subjects
    op.create_table(
        'major_subjects',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('major_id', sa.Integer(), sa.ForeignKey('majors.id'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=False),
        sa.Column('course_type', sa.String(20), nullable=False),
        sa.Column('credits', sa.Float(), nullable=True),
        sa.Column('sort_order', sa.Integer(), server_default=sa.text('0')),
        sa.UniqueConstraint('major_id', 'subject_id', name='uq_major_subjects'),
    )
    op.create_index('ix_major_subjects_major', 'major_subjects', ['major_id'])

    # user_enrollments
    op.create_table(
        'user_enrollments',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('major_id', sa.Integer(), sa.ForeignKey('majors.id'), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('1')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'major_id', name='uq_user_enrollment'),
    )
    op.create_index('ix_user_enrollments_user', 'user_enrollments', ['user_id'])

    # user_subject_status
    op.create_table(
        'user_subject_status',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id'), nullable=False),
        sa.Column('enrollment_id', sa.Integer(), sa.ForeignKey('user_enrollments.id'), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='not_taken'),
        sa.Column('score', sa.Float(), nullable=True),
        sa.Column('exam_date', sa.Date(), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default=sa.text('0')),
        sa.Column('certificate_no', sa.String(50), nullable=True),
        sa.Column('note', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint('user_id', 'subject_id', 'enrollment_id', name='uq_user_subject_status'),
    )
    op.create_index('ix_user_subject_status_user', 'user_subject_status', ['user_id'])
    op.create_index('ix_user_subject_status_enrollment', 'user_subject_status', ['enrollment_id'])


def downgrade() -> None:
    op.drop_table('user_subject_status')
    op.drop_table('user_enrollments')
    op.drop_table('major_subjects')
    op.drop_table('majors')
    op.drop_table('schools')
    op.drop_table('provinces')
