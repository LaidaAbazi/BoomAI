"""merge_heads

Revision ID: 05df29aceeff
Revises: 
Create Date: 2025-09-16 14:23:02.871389

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '05df29aceeff'
down_revision = ('add_subscription_fields', 'add_teams_user_fields', 'add_podcast_audio_fields', '5f0900a2caf3')
branch_labels = None
depends_on = None


def upgrade():
    pass


def downgrade():
    pass
