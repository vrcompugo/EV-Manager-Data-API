"""data fpr status

Revision ID: 271e06a87763
Revises: db48589a8915
Create Date: 2022-05-03 11:14:07.543520

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '271e06a87763'
down_revision = 'db48589a8915'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('contract_status', sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('contract_status', 'data')
    # ### end Alembic commands ###