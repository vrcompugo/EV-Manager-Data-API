"""survey offer_id

Revision ID: 674f8ccc4fe8
Revises: 884ffbbd4189
Create Date: 2019-07-16 13:19:41.931434

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '674f8ccc4fe8'
down_revision = '884ffbbd4189'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index('ix_user_role_version_end_transaction_id', table_name='user_role_version')
    op.drop_index('ix_user_role_version_operation_type', table_name='user_role_version')
    op.drop_index('ix_user_role_version_transaction_id', table_name='user_role_version')
    op.drop_table('user_role_version')
    op.drop_index('ix_user_version_end_transaction_id', table_name='user_version')
    op.drop_index('ix_user_version_operation_type', table_name='user_version')
    op.drop_index('ix_user_version_transaction_id', table_name='user_version')
    op.drop_table('user_version')
    op.drop_index('ix_user_role_association_version_end_transaction_id', table_name='user_role_association_version')
    op.drop_index('ix_user_role_association_version_operation_type', table_name='user_role_association_version')
    op.drop_index('ix_user_role_association_version_transaction_id', table_name='user_role_association_version')
    op.drop_table('user_role_association_version')
    op.add_column('offer', sa.Column('survey_id', sa.Integer(), nullable=True))
    op.create_foreign_key(None, 'offer', 'survey', ['survey_id'], ['id'])
    op.add_column('offer_version', sa.Column('survey_id', sa.Integer(), autoincrement=False, nullable=True))
    op.add_column('product', sa.Column('type', sa.String(length=80), nullable=True))
    op.add_column('product_version', sa.Column('type', sa.String(length=80), autoincrement=False, nullable=True))
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_column('product_version', 'type')
    op.drop_column('product', 'type')
    op.drop_column('offer_version', 'survey_id')
    op.drop_constraint(None, 'offer', type_='foreignkey')
    op.drop_column('offer', 'survey_id')
    op.create_table('user_role_association_version',
    sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('user_role_id', sa.INTEGER(), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('operation_type', sa.SMALLINT(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('transaction_id', name='user_role_association_version_pkey')
    )
    op.create_index('ix_user_role_association_version_transaction_id', 'user_role_association_version', ['transaction_id'], unique=False)
    op.create_index('ix_user_role_association_version_operation_type', 'user_role_association_version', ['operation_type'], unique=False)
    op.create_index('ix_user_role_association_version_end_transaction_id', 'user_role_association_version', ['end_transaction_id'], unique=False)
    op.create_table('user_version',
    sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('email', sa.VARCHAR(length=255), autoincrement=False, nullable=True),
    sa.Column('registered_on', postgresql.TIMESTAMP(), autoincrement=False, nullable=True),
    sa.Column('username', sa.VARCHAR(length=50), autoincrement=False, nullable=True),
    sa.Column('password_hash', sa.VARCHAR(length=100), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('operation_type', sa.SMALLINT(), autoincrement=False, nullable=False),
    sa.PrimaryKeyConstraint('id', 'transaction_id', name='user_version_pkey')
    )
    op.create_index('ix_user_version_transaction_id', 'user_version', ['transaction_id'], unique=False)
    op.create_index('ix_user_version_operation_type', 'user_version', ['operation_type'], unique=False)
    op.create_index('ix_user_version_end_transaction_id', 'user_version', ['end_transaction_id'], unique=False)
    op.create_table('user_role_version',
    sa.Column('id', sa.INTEGER(), autoincrement=False, nullable=False),
    sa.Column('label', sa.VARCHAR(length=150), autoincrement=False, nullable=True),
    sa.Column('permissions', postgresql.JSONB(astext_type=sa.Text()), autoincrement=False, nullable=True),
    sa.Column('transaction_id', sa.BIGINT(), autoincrement=False, nullable=False),
    sa.Column('end_transaction_id', sa.BIGINT(), autoincrement=False, nullable=True),
    sa.Column('operation_type', sa.SMALLINT(), autoincrement=False, nullable=False),
    sa.Column('code', sa.VARCHAR(length=60), autoincrement=False, nullable=True),
    sa.PrimaryKeyConstraint('id', 'transaction_id', name='user_role_version_pkey')
    )
    op.create_index('ix_user_role_version_transaction_id', 'user_role_version', ['transaction_id'], unique=False)
    op.create_index('ix_user_role_version_operation_type', 'user_role_version', ['operation_type'], unique=False)
    op.create_index('ix_user_role_version_end_transaction_id', 'user_role_version', ['end_transaction_id'], unique=False)
    # ### end Alembic commands ###
