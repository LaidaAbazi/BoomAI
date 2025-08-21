"""Merge heads: sentiment chart data and color field

Revision ID: 5f0900a2caf3
Revises: 78374a535955, add_color_field_to_labels
Create Date: 2025-08-21 10:42:33.455891

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '5f0900a2caf3'
down_revision = ('78374a535955', 'add_color_field_to_labels')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
