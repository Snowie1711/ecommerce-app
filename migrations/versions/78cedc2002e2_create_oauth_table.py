"""Create OAuth table

Revision ID: 78cedc2002e2
Revises: 339470a9f210
Create Date: 2025-04-08 13:57:03.012152

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78cedc2002e2'
down_revision = '339470a9f210'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('oauth',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('token', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('oauth')
    # ### end Alembic commands ###
