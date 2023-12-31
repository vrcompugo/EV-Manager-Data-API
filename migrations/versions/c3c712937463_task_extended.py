"""task extended

Revision ID: c3c712937463
Revises: 938fb80e3dce
Create Date: 2020-03-12 15:39:57.150190

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c3c712937463'
down_revision = '938fb80e3dce'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('task', sa.Column('deadline', sa.DateTime(), nullable=True))
    op.add_column('task', sa.Column('remote_id', sa.Integer(), nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('task', 'remote_id')
    op.drop_column('task', 'deadline')
    # ### end Alembic commands ###
