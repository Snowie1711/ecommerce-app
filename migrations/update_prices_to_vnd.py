"""Update product prices from USD to VND"""
from flask import current_app
from models import db, Product

def upgrade():
    """Convert all prices from USD to VND"""
    try:
        products = Product.query.all()
        for product in products:
            # Convert USD to VND and round to nearest 1000
            product.price = round(product.price * 23000, -3)
        
        db.session.commit()
        current_app.logger.info("Successfully converted all prices to VND")
    except Exception as e:
        current_app.logger.error(f"Error converting prices to VND: {str(e)}")
        db.session.rollback()

def downgrade():
    """Convert prices back to USD"""
    try:
        products = Product.query.all()
        for product in products:
            # Convert VND back to USD
            product.price = round(product.price / 23000, 2)
        
        db.session.commit()
        current_app.logger.info("Successfully converted all prices back to USD")
    except Exception as e:
        current_app.logger.error(f"Error converting prices back to USD: {str(e)}")
        db.session.rollback()