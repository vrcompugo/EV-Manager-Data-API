"""customer phone added

Revision ID: a9e2f49df31b
Revises: f49f71d929a0
Create Date: 2020-01-08 11:17:34.196002

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a9e2f49df31b'
down_revision = 'f49f71d929a0'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer', sa.Column('phone', sa.String(length=80), nullable=True))
    op.add_column('customer_version', sa.Column('phone', sa.String(length=80), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('customer_version', 'phone')
    op.drop_column('customer', 'phone')
    # ### end Alembic commands ###
