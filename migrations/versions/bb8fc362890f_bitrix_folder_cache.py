"""bitrix folder cache

Revision ID: bb8fc362890f
Revises: 67fba8668bc7
Create Date: 2021-01-14 08:20:30.829077

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'bb8fc362890f'
down_revision = '67fba8668bc7'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bitrix_folder',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('bitrix_id', sa.Integer(), nullable=True),
    sa.Column('parent_folder_id', sa.Integer(), nullable=True),
    sa.Column('path', sa.String(length=250), nullable=True),
    sa.Column('data', sa.JSON(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('bitrix_folder_version',
    sa.Column('id', sa.Integer(), autoincrement=False, nullable=False),
    sa.Column('bitrix_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('parent_folder_id', sa.Integer(), autoincrement=False, nullable=True),
    sa.Column('path', sa.String(length=250), autoincrement=False, nullable=True),
    sa.Column('data', sa.JSON(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BigInteger(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BigInteger(), nullable=True),
    sa.Column('operation_type', sa.SmallInteger(), nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id')
    )
    op.create_index(op.f('ix_bitrix_folder_version_end_transaction_id'), 'bitrix_folder_version', ['end_transaction_id'], unique=False)
    op.create_index(op.f('ix_bitrix_folder_version_operation_type'), 'bitrix_folder_version', ['operation_type'], unique=False)
    op.create_index(op.f('ix_bitrix_folder_version_transaction_id'), 'bitrix_folder_version', ['transaction_id'], unique=False)
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_bitrix_folder_version_transaction_id'), table_name='bitrix_folder_version')
    op.drop_index(op.f('ix_bitrix_folder_version_operation_type'), table_name='bitrix_folder_version')
    op.drop_index(op.f('ix_bitrix_folder_version_end_transaction_id'), table_name='bitrix_folder_version')
    op.drop_table('bitrix_folder_version')
    op.drop_table('bitrix_folder')
    # ### end Alembic commands ###
