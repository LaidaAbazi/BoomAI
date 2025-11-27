"""Add language field to case_studies

Revision ID: add_language_to_case_studies
Revises: 9a3552039129
Create Date: 2025-01-27 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_language_to_case_studies'
down_revision = '9a3552039129'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('case_studies', schema=None) as batch_op:
        batch_op.add_column(sa.Column('language', sa.String(length=50), nullable=True))


def downgrade():
    with op.batch_alter_table('case_studies', schema=None) as batch_op:
        batch_op.drop_column('language')

