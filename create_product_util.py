from app import create_app
from extensions import db
from models import Product
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_product_stock_values():
    """
    Utility function to correct stock values for all products
    """
    app = create_app()
    
    with app.app_context():
        try:
            # Get all products
            products = Product.query.all()
            logger.info(f"Found {len(products)} products")
            
            # Track changes
            updated_count = 0
            
            for product in products:
                old_stock = product.stock
                
                # Recalculate stock based on inventory type
                if product.inventory_type == 'size':
                    new_stock = sum(size.stock for size in product.sizes)
                elif product.inventory_type == 'color':
                    new_stock = sum(color.stock for color in product.colors)
                elif product.inventory_type == 'both':
                    new_stock = sum(variant.stock for variant in product.variants)
                else:
                    # For regular products, keep existing stock
                    new_stock = product.stock
                
                # Update if different
                if old_stock != new_stock:
                    logger.info(f"Updating product {product.id} '{product.name}' stock: {old_stock} -> {new_stock}")
                    product.stock = new_stock
                    updated_count += 1
            
            # Save changes
            db.session.commit()
            logger.info(f"Updated stock values for {updated_count} products")
            
        except Exception as e:
            logger.error(f"Error fixing product stock values: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    fix_product_stock_values()
