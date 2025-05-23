"""Add shipping fields to Order model

Revision ID: d481cb7c1a55
Revises: e853a6ed6717
Create Date: 2025-04-15 22:46:52.890060

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd481cb7c1a55'
down_revision = 'e853a6ed6717'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('_alembic_tmp_notifications')
    with op.batch_alter_table('notifications', schema=None) as batch_op:
        batch_op.alter_column('is_read',
               existing_type=sa.BOOLEAN(),
               nullable=True)
        batch_op.alter_column('created_at',
               existing_type=sa.DATETIME(),
               nullable=True)

    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.add_column(sa.Column('shipping_first_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('shipping_last_name', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('shipping_address2', sa.String(length=200), nullable=True))
        batch_op.add_column(sa.Column('shipping_city', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('shipping_state', sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column('shipping_zip', sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column('shipping_phone', sa.String(length=20), nullable=True))
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

    with op.batch_alter_table('product_variant', schema=None) as batch_op:
       batch_op.alter_column('stock',
        existing_type=sa.INTEGER(),
        nullable=True,
        existing_server_default=sa.text('0')
    )

    # ✅ Không drop constraint nếu chưa từng đặt tên (tránh lỗi)
    # ➕ Tạo mới foreign key với tên rõ ràng
       batch_op.create_foreign_key('fk_product_variant_color_id_product_colors', 'product_colors', ['color_id'], ['id'], ondelete='CASCADE')
       batch_op.create_foreign_key('fk_product_variant_size_id_product_sizes', 'product_sizes', ['size_id'], ['id'], ondelete='CASCADE')
       batch_op.create_foreign_key('fk_product_variant_product_id_products', 'products', ['product_id'], ['id'], ondelete='CASCADE')



    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.alter_column('comment',
               existing_type=sa.TEXT(),
               nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('review', schema=None) as batch_op:
        batch_op.alter_column('comment',
               existing_type=sa.TEXT(),
               nullable=True)

    with op.batch_alter_table('product_variant', schema=None) as batch_op:
    # ✅ Xóa đúng constraint đã tạo
       batch_op.drop_constraint('fk_product_variant_color_id_product_colors', type_='foreignkey')
       batch_op.drop_constraint('fk_product_variant_size_id_product_sizes', type_='foreignkey')
       batch_op.drop_constraint('fk_product_variant_product_id_products', type_='foreignkey')

    # ➕ Có thể tạo lại constraint mặc định (không cần thiết nếu downgrade không yêu cầu tái tạo)
       batch_op.alter_column('stock',
              existing_type=sa.INTEGER(),
              nullable=False,
              existing_server_default=sa.text('0')
    )



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

    op.create_table('_alembic_tmp_notifications',
    sa.Column('id', sa.INTEGER(), nullable=False),
    sa.Column('user_id', sa.INTEGER(), nullable=False),
    sa.Column('message', sa.VARCHAR(length=255), nullable=False),
    sa.Column('link', sa.VARCHAR(length=255), nullable=True),
    sa.Column('is_read', sa.BOOLEAN(), nullable=True),
    sa.Column('created_at', sa.DATETIME(), nullable=True),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###
