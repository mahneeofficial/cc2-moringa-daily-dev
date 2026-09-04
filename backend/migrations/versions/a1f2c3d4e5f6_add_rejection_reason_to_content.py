"""add rejection reason to content

Revision ID: a1f2c3d4e5f6
Revises: add_thumbnail_url
"""

from alembic import op
import sqlalchemy as sa


revision = "a1f2c3d4e5f6"
down_revision = "add_thumbnail_url"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("content", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("RejectionReason", sa.Text(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("content", schema=None) as batch_op:
        batch_op.drop_column("RejectionReason")
