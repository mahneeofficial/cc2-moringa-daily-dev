"""add thumbnail url to content

Revision ID: add_thumbnail_url
Revises: 6aa238642ae6
"""

from alembic import op
import sqlalchemy as sa


revision = "add_thumbnail_url"
down_revision = "6aa238642ae6"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("content", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("ThumbnailURL", sa.String(length=500), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("content", schema=None) as batch_op:
        batch_op.drop_column("ThumbnailURL")
