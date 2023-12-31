"""customer db reseller_id added

Revision ID: 460590aae513
Revises: a9e2f49df31b
Create Date: 2020-01-08 11:32:09.567870

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '460590aae513'
down_revision = 'a9e2f49df31b'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('customer', sa.Column('reseller_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'customer', 'reseller', ['reseller_id'], ['id'])
    op.add_column('customer_version', sa.Column('reseller_id', sa.Integer(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('customer_version', 'reseller_id')
    op.drop_constraint(None, 'customer', type_='foreignkey')
    op.drop_column('customer', 'reseller_id')
    # ### end Alembic commands ###
