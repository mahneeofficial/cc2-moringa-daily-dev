"""Allow pending content status

Revision ID: 6aa238642ae6
Revises: 0b663a96b349
"""

from alembic import op
import sqlalchemy as sa


revision = '6aa238642ae6'
down_revision = '0b663a96b349'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('content', schema=None, recreate='always') as batch_op:
        batch_op.drop_constraint(
            'check_valid_content_status',
            type_='check'
        )

        batch_op.create_check_constraint(
            'check_valid_content_status',
            '"Status" IN (\'Draft\', \'Pending\', \'Published\', \'Archived\')'
        )


def downgrade():
    with op.batch_alter_table('content', schema=None, recreate='always') as batch_op:
        batch_op.drop_constraint(
            'check_valid_content_status',
            type_='check'
        )

        batch_op.create_check_constraint(
            'check_valid_content_status',
            '"Status" IN (\'Draft\', \'Published\', \'Archived\')'
        )
