"""Add LinkedIn post variation fields to case_studies

Revision ID: add_linkedin_post_variations
Revises: add_case_study_submission_fields
Create Date: 2025-12-02 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'add_linkedin_post_variations'
down_revision = 'add_case_study_submission_fields'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_columns = [col['name'] for col in inspector.get_columns('case_studies')] if 'case_studies' in existing_tables else []
    
    # Add linkedin_post_confident field if it doesn't exist
    if 'linkedin_post_confident' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('linkedin_post_confident', sa.Text(), nullable=True)
        )
    else:
        print("case_studies.linkedin_post_confident column already exists, skipping")
    
    # Add linkedin_post_pragmatic field if it doesn't exist
    if 'linkedin_post_pragmatic' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('linkedin_post_pragmatic', sa.Text(), nullable=True)
        )
    else:
        print("case_studies.linkedin_post_pragmatic column already exists, skipping")
    
    # Add linkedin_post_standard field if it doesn't exist
    if 'linkedin_post_standard' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('linkedin_post_standard', sa.Text(), nullable=True)
        )
    else:
        print("case_studies.linkedin_post_standard column already exists, skipping")
    
    # Add linkedin_post_formal field if it doesn't exist
    if 'linkedin_post_formal' not in existing_columns:
        op.add_column(
            'case_studies',
            sa.Column('linkedin_post_formal', sa.Text(), nullable=True)
        )
    else:
        print("case_studies.linkedin_post_formal column already exists, skipping")


def downgrade():
    op.drop_column('case_studies', 'linkedin_post_formal')
    op.drop_column('case_studies', 'linkedin_post_standard')
    op.drop_column('case_studies', 'linkedin_post_pragmatic')
    op.drop_column('case_studies', 'linkedin_post_confident')
