"""Add Teams user connection fields

Revision ID: add_teams_user_fields
Revises: df1a7d34cf6b
Create Date: 2024-01-15 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_teams_user_fields'
down_revision = 'df1a7d34cf6b'
branch_labels = None
depends_on = None


def upgrade():
    # Add Teams connection fields to users table
    op.add_column('users', sa.Column('teams_connected', sa.Boolean(), nullable=True, default=False))
    op.add_column('users', sa.Column('teams_user_id', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('teams_tenant_id', sa.String(length=100), nullable=True))
    op.add_column('users', sa.Column('teams_user_token', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('teams_scope', sa.String(length=500), nullable=True))
    op.add_column('users', sa.Column('teams_authed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    # Remove Teams connection fields from users table
    op.drop_column('users', 'teams_authed_at')
    op.drop_column('users', 'teams_scope')
    op.drop_column('users', 'teams_user_token')
    op.drop_column('users', 'teams_tenant_id')
    op.drop_column('users', 'teams_user_id')
    op.drop_column('users', 'teams_connected')
