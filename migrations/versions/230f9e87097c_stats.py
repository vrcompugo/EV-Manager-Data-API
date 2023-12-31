"""stats

Revision ID: 230f9e87097c
Revises: 1155e607f8e4
Create Date: 2022-03-16 12:48:52.444962

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '230f9e87097c'
down_revision = '1155e607f8e4'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('bitrix24_file_cache',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('drive_id', sa.String(length=30), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('is_static', sa.Boolean(), nullable=True),
    sa.Column('content', sa.LargeBinary(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('bitrix24_product_cache',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('product_id', sa.String(length=30), nullable=True),
    sa.Column('name', sa.String(length=255), nullable=True),
    sa.Column('catalog_id', sa.String(length=30), nullable=True),
    sa.Column('section_id', sa.String(length=30), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('bitrix24_request_cache',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('method', sa.String(length=20), nullable=True),
    sa.Column('url', sa.String(length=255), nullable=True),
    sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('post_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('domain', sa.String(length=255), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('cached_responses', sa.Integer(), nullable=True),
    sa.Column('fresh_response', sa.Integer(), nullable=True),
    sa.Column('response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('request_log',
    sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
    sa.Column('url', sa.String(length=255), nullable=True),
    sa.Column('route', sa.String(length=255), nullable=True),
    sa.Column('method', sa.String(length=20), nullable=True),
    sa.Column('post_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('datetime', sa.DateTime(), nullable=True),
    sa.Column('duration_milliseconds', sa.Integer(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('request_log')
    op.drop_table('bitrix24_request_cache')
    op.drop_table('bitrix24_product_cache')
    op.drop_table('bitrix24_file_cache')
    # ### end Alembic commands ###
