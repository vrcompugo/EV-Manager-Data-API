"""user association table

Revision ID: c23a38d61e52
Revises: a8e29c449a4a
Create Date: 2020-11-24 10:36:22.567667

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c23a38d61e52'
down_revision = 'a8e29c449a4a'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('user_zip_association',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=True),
    sa.Column('last_assigned', sa.DateTime(), nullable=True),
    sa.Column('current_cycle_index', sa.Integer(), nullable=True),
    sa.Column('current_cycle_count', sa.Integer(), nullable=True),
    sa.Column('max_leads', sa.Integer(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('comment', sa.String(length=90), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('user_zip_association')
    # ### end Alembic commands ###
