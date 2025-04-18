from app import create_app
from models.product import Product

app = create_app()
with app.app_context():
    product = Product.query.get(13)
    if product:
        print(f"Product exists: {product.name}")
        print(f"Active status: {product.is_active}")
    else:
        print("Product ID 13 does not exist in database")