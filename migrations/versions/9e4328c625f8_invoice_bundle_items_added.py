"""invoice_bundle_items added

Revision ID: 9e4328c625f8
Revises: edea5a21b255
Create Date: 2022-08-02 09:41:15.381313

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '9e4328c625f8'
down_revision = 'edea5a21b255'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('invoice_bundle_item', sa.Column('contract_number', sa.String(length=150), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('customer_city', sa.String(length=150), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('customer_name', sa.String(length=150), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('customer_number', sa.String(length=150), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('customer_street', sa.String(length=250), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('customer_zip', sa.String(length=20), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('total', sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column('invoice_bundle_item', sa.Column('total_net', sa.Numeric(precision=12, scale=4), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('invoice_bundle_item', 'total_net')
    op.drop_column('invoice_bundle_item', 'total')
    op.drop_column('invoice_bundle_item', 'customer_zip')
    op.drop_column('invoice_bundle_item', 'customer_street')
    op.drop_column('invoice_bundle_item', 'customer_number')
    op.drop_column('invoice_bundle_item', 'customer_name')
    op.drop_column('invoice_bundle_item', 'customer_city')
    op.drop_column('invoice_bundle_item', 'contract_number')
    # ### end Alembic commands ###