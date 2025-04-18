from app import create_app
from models import db, Product

def update_prices_to_vnd():
    """Convert all prices from USD to VND"""
    app = create_app()
    with app.app_context():
        try:
            print("Starting price conversion to VND...")
            products = Product.query.all()
            for product in products:
                # Convert USD to VND as integer
                old_price = product.price
                product.price = int(product.price * 23000)
                print(f"Converting {product.name}: ${old_price:.2f} -> {product.price:,.0f}₫")
            
            db.session.commit()
            print("Successfully converted all prices to VND")
        except Exception as e:
            print(f"Error converting prices to VND: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    update_prices_to_vnd()