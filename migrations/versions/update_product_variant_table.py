"""update product variant table

Revision ID: update_product_variant_table
Revises: update_price_columns
Create Date: 2025-04-15 18:45:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import text, inspect
from sqlalchemy.engine.reflection import Inspector

# Add a unique revision ID - this should be a unique identifier string
# Using a timestamp-based format that Alembic typically generates
revision = 'a1b2c3d4e5f6'  # You may need to adjust this to avoid conflicts with other migrations

# Add down_revision if it's missing as well (reference to the previous migration)
# If this is the first migration, set it to None
down_revision = None  # Replace with the actual parent revision ID if known

def table_exists(table_name):
    conn = op.get_bind()
    insp = sa.inspect(conn)
    return table_name in insp.get_table_names()

def drop_table_if_exists(table_name):
    if table_exists(table_name):
        op.drop_table(table_name)

def upgrade():
    # Drop old tables if they exist
    old_tables = ['product_variant', 'product_size', 'product_color']
    for table in old_tables:
        drop_table_if_exists(table)

    # Check if product_sizes table already exists before creating it
    connection = op.get_bind()
    inspector = sa.inspect(connection)
    tables = inspector.get_table_names()
    
    # Only create product_sizes table if it doesn't exist
    if 'product_sizes' not in tables:
        op.create_table('product_sizes',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('size', sa.String(20), nullable=False),
            sa.Column('stock', sa.Integer(), nullable=False, server_default=text('0')),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Only create product_colors table if it doesn't exist
    if 'product_colors' not in tables:
        op.create_table('product_colors',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('color_name', sa.String(50), nullable=False),
            sa.Column('color_code', sa.String(20), nullable=True),
            sa.Column('stock', sa.Integer(), nullable=False, server_default=text('0')),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Only create product_variant table if it doesn't exist
    if 'product_variant' not in tables:
        op.create_table('product_variant',
            sa.Column('id', sa.Integer(), nullable=False),
            sa.Column('product_id', sa.Integer(), nullable=False),
            sa.Column('size_id', sa.Integer(), nullable=False),
            sa.Column('color_id', sa.Integer(), nullable=False),
            sa.Column('stock', sa.Integer(), nullable=False, server_default=text('0')),
            sa.ForeignKeyConstraint(['product_id'], ['products.id'], ),
            sa.ForeignKeyConstraint(['size_id'], ['product_sizes.id'], ),
            sa.ForeignKeyConstraint(['color_id'], ['product_colors.id'], ),
            sa.PrimaryKeyConstraint('id')
        )

    # Also update the product_sizes and product_colors tables to use server_default
    op.execute("ALTER TABLE product_sizes ALTER COLUMN stock SET DEFAULT 0")
    op.execute("ALTER TABLE product_colors ALTER COLUMN stock SET DEFAULT 0")

def downgrade():
    # Drop tables in reverse order
    for table in ['product_variant', 'product_colors', 'product_sizes']:
        drop_table_if_exists(table)