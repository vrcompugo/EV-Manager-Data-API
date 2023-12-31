"""s3 file with bitrix_id

Revision ID: a8e29c449a4a
Revises: c7706d81b0f5
Create Date: 2020-10-28 15:30:55.846736

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a8e29c449a4a'
down_revision = 'c7706d81b0f5'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.add_column('s3_file', sa.Column('bitrix_file_id', sa.Integer(), nullable=True))
    op.add_column('s3_file_version', sa.Column('bitrix_file_id', sa.Integer(), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('s3_file_version', 'bitrix_file_id')
    op.drop_column('s3_file', 'bitrix_file_id')
    # ### end Alembic commands ###
