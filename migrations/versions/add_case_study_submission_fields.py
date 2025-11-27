"""Add submission fields to case_studies

Revision ID: add_case_study_submission_fields
Revises: add_company_and_roles
Create Date: 2025-11-26 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_case_study_submission_fields'
down_revision = 'add_company_and_roles'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_columns = [col['name'] for col in inspector.get_columns('case_studies')] if 'case_studies' in existing_tables else []
    
    # Add submitted field if it doesn't exist
    if 'submitted' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('submitted', sa.Boolean(), nullable=True, server_default=sa.text('false'))
        )
    else:
        print("case_studies.submitted column already exists, skipping")
    
    # Add submitted_at field if it doesn't exist
    if 'submitted_at' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True)
        )
    else:
        print("case_studies.submitted_at column already exists, skipping")
    
    # Set default value for existing rows
    if 'submitted' in existing_columns:
        # Column exists but might not have default, update existing rows
        conn = bind
        conn.execute(sa.text("UPDATE case_studies SET submitted = false WHERE submitted IS NULL"))
    else:
        # Column was just added, set default for existing rows
        conn = bind
        conn.execute(sa.text("UPDATE case_studies SET submitted = false WHERE submitted IS NULL"))


def downgrade():
    op.drop_column('case_studies', 'submitted_at')
    op.drop_column('case_studies', 'submitted')

