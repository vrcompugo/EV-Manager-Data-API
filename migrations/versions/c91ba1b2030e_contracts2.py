"""contracts2

Revision ID: c91ba1b2030e
Revises: c4007ed4741b
Create Date: 2022-03-03 17:28:13.219128

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'c91ba1b2030e'
down_revision = 'c4007ed4741b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('contract2',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('contract_number', sa.String(length=50), nullable=True),
    sa.Column('first_name', sa.String(length=50), nullable=True),
    sa.Column('last_name', sa.String(length=50), nullable=True),
    sa.Column('street', sa.String(length=50), nullable=True),
    sa.Column('street_nb', sa.String(length=50), nullable=True),
    sa.Column('zip', sa.String(length=50), nullable=True),
    sa.Column('city', sa.String(length=50), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('contract2')
    # ### end Alembic commands ###