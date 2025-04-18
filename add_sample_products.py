from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from models import Category, Product, ProductSize, ProductColor, db
import random
import os
from config import Config

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

# Sample product data templates
clothing_names = [
    "Classic {category} in {color}",
    "Premium {category} - {style}",
    "Sports {category} {color}",
    "Modern {category} {style}",
    "Casual {category} in {color}",
    "Trendy {category} - {style}",
    "Designer {category} {color}",
    "Urban {category} {style}",
    "Essential {category} in {color}",
    "Signature {category} - {style}"
]

electronics_names = [
    "Pro {category} X{model}",
    "Smart {category} Elite",
    "Ultra {category} {model}",
    "Premium {category} Pro",
    "{brand} {category} Plus",
    "Advanced {category} {model}",
    "Elite {category} Series",
    "Next-Gen {category}",
    "Digital {category} Pro",
    "Tech {category} {model}"
]

colors = ["Red", "Blue", "Black", "White", "Gray", "Navy", "Green", "Purple", "Brown", "Beige"]
styles = ["Slim Fit", "Regular Fit", "Loose Fit", "Athletic", "Vintage", "Modern", "Classic", "Trendy", "Casual", "Elegant"]
brands = ["TechPro", "SmartLife", "DigiMax", "EliteTech", "NextGen"]
sizes = ["S", "M", "L", "XL", "XXL"]
shoe_sizes = ["38", "39", "40", "41", "42", "43", "44"]

def generate_sku(category_name, index):
    prefix = ''.join(word[0].upper() for word in category_name.split())
    return f"{prefix}{index:03d}"

def create_sample_products():
    with app.app_context():
        categories = Category.query.all()
        
        for category in categories:
            print(f"Creating sample products for category: {category.name}")
            
            for i in range(10):
                # Generate basic product info
                if category.has_sizes:  # Clothing or shoes
                    name = clothing_names[i].format(
                        category=category.name,
                        color=random.choice(colors),
                        style=random.choice(styles)
                    )
                    base_price = random.randint(200000, 2000000)  # 200k - 2M VND
                else:  # Electronics or other categories
                    name = electronics_names[i].format(
                        category=category.name,
                        model=random.randint(1000, 9999),
                        brand=random.choice(brands)
                    )
                    base_price = random.randint(1000000, 10000000)  # 1M - 10M VND

                # Create the product
                product = Product(
                    name=name,
                    description=f"High-quality {category.name.lower()} for all occasions. Premium materials and excellent craftsmanship.",
                    price=base_price,
                    stock=0,  # Will be updated based on sizes/colors
                    category_id=category.id,
                    sku=generate_sku(category.name, i + 1),
                    is_active=True,
                    has_sizes=category.has_sizes
                )
                db.session.add(product)
                db.session.flush()  # Get product ID

                # Add sizes if applicable
                if category.has_sizes:
                    size_list = shoe_sizes if "shoes" in category.name.lower() else sizes
                    total_stock = 0
                    for size in size_list:
                        stock = random.randint(5, 20)
                        total_stock += stock
                        size_entry = ProductSize(
                            product=product,
                            size=size,
                            stock=stock
                        )
                        db.session.add(size_entry)
                    product.stock = total_stock
                else:
                    # Add colors with stock for non-sized products
                    total_stock = 0
                    for _ in range(random.randint(2, 4)):  # 2-4 color variants
                        color_name = random.choice(colors)
                        stock = random.randint(5, 20)
                        total_stock += stock
                        color = ProductColor(
                            product=product,
                            color_name=color_name,
                            color_code=f"#{random.randint(0, 0xFFFFFF):06x}",  # Random hex color
                            stock=stock
                        )
                        db.session.add(color)
                    product.stock = total_stock

            try:
                db.session.commit()
                print(f"Added 10 products to category: {category.name}")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding products to category {category.name}: {str(e)}")

if __name__ == "__main__":
    create_sample_products()
    print("Sample products creation completed!")