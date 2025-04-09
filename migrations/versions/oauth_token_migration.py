"""Add oauth_token field

Revision ID: oauth_token_migration
Create Date: 2025-04-07 21:12:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'oauth_token_migration'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('oauth_token', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('users', 'oauth_token')