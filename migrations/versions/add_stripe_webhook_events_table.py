"""Add stripe_webhook_events table for idempotency

Revision ID: add_stripe_webhook_events
Revises: 9a3552039129
Create Date: 2025-11-17 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'add_stripe_webhook_events'
down_revision = '9a3552039129'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'stripe_webhook_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('processed', sa.Boolean(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id')
    )
    op.create_index('ix_stripe_webhook_events_event_id', 'stripe_webhook_events', ['event_id'], unique=False)


def downgrade():
    op.drop_index('ix_stripe_webhook_events_event_id', table_name='stripe_webhook_events')
    op.drop_table('stripe_webhook_events')

