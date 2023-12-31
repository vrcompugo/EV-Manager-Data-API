"""user_departments

Revision ID: 80b109f7b676
Revises: f48a01a6e7cc
Create Date: 2023-02-08 16:12:46.840567

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '80b109f7b676'
down_revision = 'f48a01a6e7cc'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.add_column('user', sa.Column('bitrix_department_ids', sa.JSON(), nullable=True))
    op.add_column('user', sa.Column('bitrix_user_id', sa.String(length=50), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('user', 'bitrix_user_id')
    op.drop_column('user', 'bitrix_department_ids')
    # ### end Alembic commands ###
