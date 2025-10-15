"""Add podcast audio fields to case_studies

Revision ID: add_podcast_audio_fields
Revises: df1a7d34cf6b
Create Date: 2025-10-06 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_podcast_audio_fields'
down_revision = 'df1a7d34cf6b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('case_studies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('podcast_audio_data', sa.LargeBinary(), nullable=True))
        batch_op.add_column(sa.Column('podcast_audio_mime', sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column('podcast_audio_size', sa.Integer(), nullable=True))


def downgrade():
    with op.batch_alter_table('case_studies', schema=None) as batch_op:
        batch_op.drop_column('podcast_audio_size')
        batch_op.drop_column('podcast_audio_mime')
        batch_op.drop_column('podcast_audio_data')


