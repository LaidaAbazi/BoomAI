"""Final merge of all outstanding heads

Revision ID: merge_all_heads_20251015
Revises: add_subscription_fields, add_teams_user_fields, add_podcast_audio_fields, 5f0900a2caf3
Create Date: 2025-10-15 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_all_heads_20251015'
down_revision = ('add_subscription_fields', 'add_teams_user_fields', 'add_podcast_audio_fields', '5f0900a2caf3')
branch_labels = None
depends_on = None


def upgrade():
    # This is a no-op merge migration.
    pass


def downgrade():
    # This is a no-op merge migration.
    pass


