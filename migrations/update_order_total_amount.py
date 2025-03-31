from alembic import op
import sqlalchemy as sa

def upgrade():
    # Alter column type from FLOAT to INTEGER
    op.alter_column('orders', 'total_amount',
                    existing_type=sa.Float(),
                    type_=sa.Integer(),
                    existing_nullable=False)

def downgrade():
    # Revert back to FLOAT if needed
    op.alter_column('orders', 'total_amount',
                    existing_type=sa.Integer(),
                    type_=sa.Float(),
                    existing_nullable=False)