"""Add OAuth model and profile picture

Revision ID: 339470a9f210
Revises: add_oauth_provider
Create Date: 2025-04-08 13:40:04.775493

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '339470a9f210'
down_revision = 'add_oauth_provider'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('profile_picture', sa.String(length=500), nullable=True))
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=80),
               nullable=True)
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=200),
               nullable=True)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.alter_column('password_hash',
               existing_type=sa.VARCHAR(length=200),
               nullable=False)
        batch_op.alter_column('username',
               existing_type=sa.VARCHAR(length=80),
               nullable=False)
        batch_op.drop_column('profile_picture')
    # ### end Alembic commands ###
