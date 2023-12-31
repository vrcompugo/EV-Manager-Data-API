"""insign log

Revision ID: 1fbaa728bec0
Revises: 92fc44a63b1d
Create Date: 2022-02-21 14:48:47.622339

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '1fbaa728bec0'
down_revision = '92fc44a63b1d'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('insign_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('lead_id', sa.Integer(), nullable=True),
    sa.Column('session_id', sa.String(length=120), nullable=True),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('insign_log')
    # ### end Alembic commands ###
