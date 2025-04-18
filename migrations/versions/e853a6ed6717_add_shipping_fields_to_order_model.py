"""Add shipping fields to Order model

Revision ID: e853a6ed6717
Revises: a1b2c3d4e5f6
Create Date: 2025-04-15 22:43:42.807234

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import sqlite

# revision identifiers, used by Alembic.
revision = 'e853a6ed6717'
down_revision = 'a1b2c3d4e5f6'
branch_labels = None
depends_on = None


def upgrade():
    # Import inspect for checking if tables exist
    from sqlalchemy import inspect
    
    # Get database connection
    connection = op.get_bind()
    inspector = inspect(connection)
    existing_tables = inspector.get_table_names()
    
    # Only try to drop 'oauth' table if it exists
    if 'oauth' in existing_tables:
        op.drop_table('oauth')
    
    # Continue with the rest of the migration
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.alter_column('is_read',
               existing_type=sa.BOOLEAN(),
               nullable=True)
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True)

    # Only add shipping columns if they don't already exist
    with op.batch_alter_table('orders', schema=None) as batch_op:
        # Check if columns exist before adding them
        columns = [c['name'] for c in inspector.get_columns('orders')]
        
        if 'shipping_first_name' not in columns:
            batch_op.add_column(sa.Column('shipping_first_name', sa.String(length=100), nullable=True))
        
        if 'shipping_last_name' not in columns:
            batch_op.add_column(sa.Column('shipping_last_name', sa.String(length=100), nullable=True))
        
        if 'shipping_address2' not in columns:
            batch_op.add_column(sa.Column('shipping_address2', sa.String(length=200), nullable=True))
        
        if 'shipping_city' not in columns:
            batch_op.add_column(sa.Column('shipping_city', sa.String(length=100), nullable=True))
        
        if 'shipping_state' not in columns:
            batch_op.add_column(sa.Column('shipping_state', sa.String(length=100), nullable=True))
        
        if 'shipping_zip' not in columns:
            batch_op.add_column(sa.Column('shipping_zip', sa.String(length=20), nullable=True))
        
        if 'shipping_phone' not in columns:
            batch_op.add_column(sa.Column('shipping_phone', sa.String(length=20), nullable=True))
        
        # Handle shipping_address column if needed - change type from TEXT to String(200)
        batch_op.alter_column('shipping_address',
               existing_type=sa.TEXT(),
               type_=sa.String(length=200),
               nullable=True)

    with op.batch_alter_table('product_colors', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=False,
               autoincrement=True)

    with op.batch_alter_table('product_sizes', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=False,
               autoincrement=True)

    # Fix the product_variant table alterations
    # Instead of using batch_alter_table which has issues with unnamed constraints
    # We'll use a different approach
    
    # First, backup the existing data
    context = op.get_context()
    
    # Get existing data
    product_variant_data = connection.execute('SELECT * FROM product_variant').fetchall()
    
    # Drop existing foreign keys and table
    # This may vary based on your actual constraints, adjust as needed
    op.drop_table('product_variant')
    
    # Recreate the table with proper constraints
    op.create_table('product_variant',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('product_id', sa.Integer(), nullable=False),
        sa.Column('size_id', sa.Integer(), nullable=True),
        sa.Column('color_id', sa.Integer(), nullable=True),
        sa.Column('stock', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['color_id'], ['product_colors.id'], name='fk_variant_color'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], name='fk_variant_product'),
        sa.ForeignKeyConstraint(['size_id'], ['product_sizes.id'], name='fk_variant_size'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # Reinsert data if needed
    if product_variant_data:
        column_names = ['id', 'product_id', 'size_id', 'color_id', 'stock', 'created_at']
        for row in product_variant_data:
            # Convert row data to dict for reinsertion
            row_dict = {column_names[i]: value for i, value in enumerate(row) if i < len(column_names)}
            op.bulk_insert(sa.table('product_variant', *[sa.column(c) for c in row_dict.keys()]), [row_dict])
    
    # Continue with the orders table changes
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.alter_column('comment',
               existing_type=sa.TEXT(),
               nullable=True)

    with op.batch_alter_table('product_variant', schema=None) as batch_op:
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.create_foreign_key(None, 'product_sizes', ['size_id'], ['id'])
        batch_op.create_foreign_key(None, 'product_colors', ['color_id'], ['id'])
        batch_op.create_foreign_key(None, 'products', ['product_id'], ['id'])
        batch_op.alter_column('stock',
               existing_type=sa.INTEGER(),
               nullable=False,
               existing_server_default=sa.text('0'))

    with op.batch_alter_table('product_sizes', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=True,
               autoincrement=True)

    with op.batch_alter_table('product_colors', schema=None) as batch_op:
        batch_op.alter_column('id',
               existing_type=sa.INTEGER(),
               nullable=True,
               autoincrement=True)

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.alter_column('shipping_address',
               existing_type=sa.String(length=200),
               type_=sa.TEXT(),
               nullable=False)
        batch_op.drop_column('shipping_phone')
        batch_op.drop_column('shipping_zip')
        batch_op.drop_column('shipping_state')
        batch_op.drop_column('shipping_city')
        batch_op.drop_column('shipping_address2')
        batch_op.drop_column('shipping_last_name')
        batch_op.drop_column('shipping_first_name')

    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=False)
        batch_op.alter_column('is_read',
               existing_type=sa.BOOLEAN(),
               nullable=False)

    op.create_table('oauth',
    sa.Column('user_id', sa.INTEGER(), nullable=True),
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('provider', sa.VARCHAR(length=50), nullable=False),
    sa.Column('created_at', sa.DATETIME(), nullable=False),
    sa.Column('token', sqlite.JSON(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
