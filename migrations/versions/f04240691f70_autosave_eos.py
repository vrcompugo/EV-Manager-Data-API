"""autosave eos

Revision ID: f04240691f70
Revises: 16cd7b1fceb4
Create Date: 2023-01-20 10:08:41.402399

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'f04240691f70'
down_revision = '16cd7b1fceb4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('quote_history', sa.Column('is_complete', sa.Boolean(), nullable=True))
    op.execute("UPDATE quote_history SET is_complete = true")

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###

    op.drop_column('quote_history', 'is_complete')

    # ### end Alembic commands ###