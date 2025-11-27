"""Merge add_company_and_roles and add_stripe_webhook_events

Revision ID: merge_company_and_stripe
Revises: add_company_and_roles, add_stripe_webhook_events
Create Date: 2025-11-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_company_and_stripe'
down_revision = ('add_company_and_roles', 'add_stripe_webhook_events')
branch_labels = None
depends_on = None


def upgrade():
    # This is a merge migration - no operations needed
    pass


def downgrade():
    # This is a merge migration - no operations needed
    pass

