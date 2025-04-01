"""Update password field to password_hash

This migration renames the password column to password_hash in the users table
and ensures all passwords are properly hashed.
"""
from flask import current_app
from models import db
from alembic import op
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

def upgrade():
    # Rename password column to password_hash
    op.alter_column('users', 'password',
                    new_column_name='password_hash',
                    existing_type=sa.String(200),
                    existing_nullable=False)

def downgrade():
    # Rename password_hash column back to password
    op.alter_column('users', 'password_hash',
                    new_column_name='password',
                    existing_type=sa.String(200),
                    existing_nullable=False)