"""Fix LinkedIn post column names to match model

Revision ID: fix_linkedin_post_column_names
Revises: add_linkedin_post_variations
Create Date: 2025-12-02 15:00:00.000000

This migration renames columns if they were created with the old names
(linkedin_post_confident_cheeky, linkedin_post_pragmatic_human, linkedin_post_formal_strategic)
to match the model (linkedin_post_confident, linkedin_post_pragmatic, linkedin_post_formal).

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = 'fix_linkedin_post_column_names'
down_revision = 'add_linkedin_post_variations'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_columns = {col['name']: col for col in inspector.get_columns('case_studies')} if 'case_studies' in existing_tables else {}
    
    # Rename linkedin_post_confident_cheeky to linkedin_post_confident if old name exists
    if 'linkedin_post_confident_cheeky' in existing_columns and 'linkedin_post_confident' not in existing_columns:
        op.alter_column('case_studies', 'linkedin_post_confident_cheeky', new_column_name='linkedin_post_confident')
        print("Renamed linkedin_post_confident_cheeky to linkedin_post_confident")
    
    # Rename linkedin_post_pragmatic_human to linkedin_post_pragmatic if old name exists
    if 'linkedin_post_pragmatic_human' in existing_columns and 'linkedin_post_pragmatic' not in existing_columns:
        op.alter_column('case_studies', 'linkedin_post_pragmatic_human', new_column_name='linkedin_post_pragmatic')
        print("Renamed linkedin_post_pragmatic_human to linkedin_post_pragmatic")
    
    # Rename linkedin_post_formal_strategic to linkedin_post_formal if old name exists
    if 'linkedin_post_formal_strategic' in existing_columns and 'linkedin_post_formal' not in existing_columns:
        op.alter_column('case_studies', 'linkedin_post_formal_strategic', new_column_name='linkedin_post_formal')
        print("Renamed linkedin_post_formal_strategic to linkedin_post_formal")


def downgrade():
    bind = op.get_bind()
    inspector = inspect(bind)
    existing_tables = inspector.get_table_names()
    existing_columns = {col['name']: col for col in inspector.get_columns('case_studies')} if 'case_studies' in existing_tables else {}
    
    # Rename back to old names if needed
    if 'linkedin_post_confident' in existing_columns and 'linkedin_post_confident_cheeky' not in existing_columns:
        with op.batch_alter_table('case_studies', schema=None) as batch_op:
            batch_op.alter_column('linkedin_post_confident', new_column_name='linkedin_post_confident_cheeky')
    
    if 'linkedin_post_pragmatic' in existing_columns and 'linkedin_post_pragmatic_human' not in existing_columns:
        with op.batch_alter_table('case_studies', schema=None) as batch_op:
            batch_op.alter_column('linkedin_post_pragmatic', new_column_name='linkedin_post_pragmatic_human')
    
    if 'linkedin_post_formal' in existing_columns and 'linkedin_post_formal_strategic' not in existing_columns:
        with op.batch_alter_table('case_studies', schema=None) as batch_op:
            batch_op.alter_column('linkedin_post_formal', new_column_name='linkedin_post_formal_strategic')
