# -*- coding: utf-8 -*-
"""add source_url to questions"""

from alembic import op
import sqlalchemy as sa

revision = 'add_source_url_001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('questions', sa.Column('source_url', sa.String(500), nullable=True))


def downgrade():
    op.drop_column('questions', 'source_url')
