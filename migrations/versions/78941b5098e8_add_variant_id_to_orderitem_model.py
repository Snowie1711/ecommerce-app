"""Add variant_id to OrderItem model

Revision ID: 78941b5098e8
Revises: d481cb7c1a55
Create Date: 2025-04-15 23:07:47.962689

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '78941b5098e8'
down_revision = 'd481cb7c1a55'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('variant_id', sa.Integer(), nullable=True))
        batch_op.alter_column('price',
               existing_type=sa.INTEGER(),
               type_=sa.Float(),
               existing_nullable=False)
        batch_op.alter_column('size',
               existing_type=sa.VARCHAR(length=10),
               type_=sa.String(length=20),
               existing_nullable=True)
        
        # ✅ Sửa lỗi: đặt tên rõ ràng cho foreign key
        batch_op.create_foreign_key(
            'fk_order_items_variant_id',  # tên constraint rõ ràng
            'product_variant',
            ['variant_id'],
            ['id']
        )

        batch_op.drop_column('created_at')


def downgrade():
    with op.batch_alter_table('order_items', schema=None) as batch_op:
        batch_op.add_column(sa.Column('created_at', sa.DATETIME(), nullable=True))
        
        # ✅ Sửa lỗi: drop theo tên constraint đã đặt ở upgrade
        batch_op.drop_constraint('fk_order_items_variant_id', type_='foreignkey')

        batch_op.alter_column('size',
               existing_type=sa.String(length=20),
               type_=sa.VARCHAR(length=10),
               existing_nullable=True)
        batch_op.alter_column('price',
               existing_type=sa.Float(),
               type_=sa.INTEGER(),
               existing_nullable=False)
        batch_op.drop_column('variant_id')

    # ### end Alembic commands ###
