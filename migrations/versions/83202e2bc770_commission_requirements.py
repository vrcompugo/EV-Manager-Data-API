"""commission requirements

Revision ID: 83202e2bc770
Revises: cf4af72bd8cb
Create Date: 2020-01-22 13:31:50.682868

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '83202e2bc770'
down_revision = 'cf4af72bd8cb'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('lead', sa.Column('commission_net', sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column('lead', sa.Column('commission_rate', sa.JSON(), nullable=True))
    op.add_column('lead', sa.Column('counted_at', sa.DateTime(), nullable=True))
    op.add_column('lead', sa.Column('discount_range', sa.String(length=30), nullable=True))
    op.add_column('lead', sa.Column('final_price_net', sa.Numeric(precision=12, scale=4), nullable=True))
    op.add_column('lead', sa.Column('returned_at', sa.DateTime(), nullable=True))
    op.add_column('lead', sa.Column('sold_options', sa.JSON(), nullable=True))
    op.add_column('lead', sa.Column('won_at', sa.DateTime(), nullable=True))
    op.add_column('lead_version', sa.Column('commission_net', sa.Numeric(precision=12, scale=4), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('commission_rate', sa.JSON(), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('counted_at', sa.DateTime(), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('discount_range', sa.String(length=30), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('final_price_net', sa.Numeric(precision=12, scale=4), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('returned_at', sa.DateTime(), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('sold_options', sa.JSON(), autoincrement=False, nullable=True))
    op.add_column('lead_version', sa.Column('won_at', sa.DateTime(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('lead_version', 'won_at')
    op.drop_column('lead_version', 'sold_options')
    op.drop_column('lead_version', 'returned_at')
    op.drop_column('lead_version', 'final_price_net')
    op.drop_column('lead_version', 'discount_range')
    op.drop_column('lead_version', 'counted_at')
    op.drop_column('lead_version', 'commission_rate')
    op.drop_column('lead_version', 'commission_net')
    op.drop_column('lead', 'won_at')
    op.drop_column('lead', 'sold_options')
    op.drop_column('lead', 'returned_at')
    op.drop_column('lead', 'final_price_net')
    op.drop_column('lead', 'discount_range')
    op.drop_column('lead', 'counted_at')
    op.drop_column('lead', 'commission_rate')
    op.drop_column('lead', 'commission_net')
    # ### end Alembic commands ###
