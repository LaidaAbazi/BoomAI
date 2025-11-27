"""merge existing heads

Revision ID: 9a3552039129
Revises: 05df29aceeff, merge_all_heads_20251015
Create Date: 2025-11-17 15:21:26.567250

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '9a3552039129'
down_revision = ('05df29aceeff', 'merge_all_heads_20251015')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
