"""mfr export buffer added

Revision ID: 831af6fcca06
Revises: 0c5968969963
Create Date: 2021-05-26 09:32:33.232194

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '831af6fcca06'
down_revision = '0c5968969963'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('mfr_export_buffer',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('task_id', sa.String(length=200), nullable=True),
    sa.Column('last_change', sa.DateTime(), nullable=True),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('mfr_export_buffer')
    # ### end Alembic commands ###