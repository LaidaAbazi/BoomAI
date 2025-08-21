"""Add color field to labels table

Revision ID: add_color_field_to_labels
Revises: df1a7d34cf6b
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from app.utils.color_utils import ColorUtils

# revision identifiers, used by Alembic.
revision = 'add_color_field_to_labels'
down_revision = 'df1a7d34cf6b'
branch_labels = None
depends_on = None


def upgrade():
    # Add color column to labels table
    op.add_column('labels', sa.Column('color', sa.String(7), nullable=True))
    
    # Update existing labels with colors based on their names
    connection = op.get_bind()
    labels_table = sa.table('labels', sa.Column('id', sa.Integer), sa.Column('name', sa.String), sa.Column('color', sa.String))
    
    # Get all existing labels
    result = connection.execute(sa.select([labels_table.c.id, labels_table.c.name]))
    labels = result.fetchall()
    
    # Update each label with a color
    for label_id, label_name in labels:
        color = ColorUtils.get_color_for_label(label_name)
        connection.execute(
            labels_table.update().where(labels_table.c.id == label_id).values(color=color)
        )
    
    # Make color column not nullable after populating it
    op.alter_column('labels', 'color', nullable=False)


def downgrade():
    # Remove color column from labels table
    op.drop_column('labels', 'color') 