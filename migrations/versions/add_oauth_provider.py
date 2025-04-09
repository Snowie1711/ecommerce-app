"""Add oauth provider field

Revision ID: add_oauth_provider
Create Date: 2025-04-07 22:07:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic
revision = 'add_oauth_provider'
down_revision = 'oauth_token_migration'
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('users', sa.Column('provider', sa.String(length=50), nullable=True))

def downgrade():
    op.drop_column('users', 'provider')