"""del user public_id

Revision ID: a0c3031a94c7
Revises: 7f069b7d2f1e
Create Date: 2019-06-25 13:41:40.223020

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a0c3031a94c7'
down_revision = '7f069b7d2f1e'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_constraint('user_public_id_key', 'user', type_='unique')
    op.drop_column('user', 'public_id')
    op.drop_column('user_version', 'public_id')
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('user_version', sa.Column('public_id', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.add_column('user', sa.Column('public_id', sa.VARCHAR(length=100), autoincrement=False, nullable=True))
    op.create_unique_constraint('user_public_id_key', 'user', ['public_id'])
    # ### end Alembic commands ###
