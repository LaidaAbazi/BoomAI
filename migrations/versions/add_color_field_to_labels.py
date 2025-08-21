"""Add color field to labels table

Revision ID: add_color_field_to_labels
Revises: df1a7d34cf6b
Create Date: 2024-01-20 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
import hashlib

# revision identifiers, used by Alembic.
revision = 'add_color_field_to_labels'
down_revision = 'df1a7d34cf6b'
branch_labels = None
depends_on = None


def get_color_for_label(label_name):
    """Get a consistent color for a label based on its name."""
    # Pastel rainbow palette with 30 colors
    pastel_colors = [
        "#FAD0D0", "#F7B7B7", "#F9C3B9", "#FAD1C2", "#FCD6B5",
        "#FDE0B2", "#FEE9B8", "#FFF1C1", "#FFF5CC", "#FFF7D6",
        "#FFF9E0", "#FFFBEA", "#EAF8CF", "#DFF5D2", "#D2F0DA",
        "#C8EEDD", "#CDEDEA", "#CBEFF2", "#CFEAF7", "#D4EEFF",
        "#DAF0FF", "#E0F2FF", "#DAD9FF", "#D7D1FF", "#D9C9FF",
        "#E0CCFF", "#E8C7FF", "#F0C8F9", "#F6C7EE", "#FAD0F0"
    ]
    
    # Create a hash of the label name
    hash_object = hashlib.md5(label_name.lower().encode())
    hash_hex = hash_object.hexdigest()
    
    # Convert hash to an integer and use modulo to get index
    hash_int = int(hash_hex[:8], 16)
    color_index = hash_int % len(pastel_colors)
    
    return pastel_colors[color_index]


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
        color = get_color_for_label(label_name)
        connection.execute(
            labels_table.update().where(labels_table.c.id == label_id).values(color=color)
        )
    
    # Make color column not nullable after populating it
    op.alter_column('labels', 'color', nullable=False)


def downgrade():
    # Remove color column from labels table
    op.drop_column('labels', 'color') 