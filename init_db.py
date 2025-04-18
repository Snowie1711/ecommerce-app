#!/usr/bin/env python
import os
from datetime import datetime, timedelta
import random
import json

# Create instance directory if it doesn't exist
if not os.path.exists('instance'):
    os.makedirs('instance')

def init_db():
    """Initialize the database with sample data"""
    from app import create_app, db
    from models import User, Product, ProductSize, ProductColor, Order, OrderItem, OrderStatus, Category, ProductImage
    
    print("Initializing database...")
    app = create_app('development')
    
    with app.app_context():
        try:
            # Drop existing tables
            print("Dropping existing tables...")
            db.drop_all()
            
            # Create all tables
            print("Creating new tables...")
            db.create_all()
            
            print("Creating admin and test users...")
            # Create admin user
            admin = User(
                email='admin@example.com',
                username='admin',
                password='Admin@123',  # Will be hashed by User model's setter
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            db.session.add(admin)
            
            # Create test user
            user = User(
                email='user@example.com',
                username='testuser',
                password='Test@123',  # Will be hashed by User model's setter
                first_name='Test',
                last_name='User'
            )
            db.session.add(user)
            db.session.flush()
            
            print("Creating categories...")
            # Define categories
            categories = {
                'Electronics': {'description': 'Electronic devices and accessories', 'has_sizes': False},
                'Sports & Outdoors': {'description': 'Sports equipment and outdoor gear', 'has_sizes': True},
                'Home & Kitchen': {'description': 'Home appliances and kitchen essentials', 'has_sizes': False},
                'Clothing': {'description': 'Apparel and fashion accessories', 'has_sizes': True},
                'Books': {'description': 'Books and publications', 'has_sizes': False}
            }
            
            category_objects = {}
            for name, data in categories.items():
                slug = name.lower().replace(' & ', '-').replace(' ', '-')
                category = Category(
                    name=name,
                    slug=slug,
                    description=data['description'],
                    has_sizes=data['has_sizes']
                )
                db.session.add(category)
                db.session.flush()
                category_objects[name] = category
            
            print("Creating sample products...")
            # Sample products
            products = [
                {
                    'name': 'Smartphone X Pro',
                    'description': 'Latest flagship smartphone with advanced features',
                    'price': 999.99,
                    'stock': 50,
                    'sku': 'PHONE-001',
                    'category': 'Electronics',
                    'colors': [
                        {'name': 'Black', 'code': '#000000', 'stock': 20},
                        {'name': 'White', 'code': '#FFFFFF', 'stock': 15},
                        {'name': 'Gold', 'code': '#FFD700', 'stock': 15}
                    ]
                },
                {
                    'name': 'Running Shoes',
                    'description': 'Lightweight running shoes with cushioning',
                    'price': 129.99,
                    'stock': 100,
                    'sku': 'SHOES-001',
                    'category': 'Clothing',
                    'sizes': ['38', '39', '40', '41', '42', '43', '44'],
                    'colors': [
                        {'name': 'Black', 'code': '#000000', 'stock': 40},
                        {'name': 'White', 'code': '#FFFFFF', 'stock': 30},
                        {'name': 'Red', 'code': '#FF0000', 'stock': 30}
                    ]
                }
            ]
            
            # Create products
            for product_data in products:
                category = category_objects[product_data.pop('category')]
                sizes = product_data.pop('sizes', [])
                colors = product_data.pop('colors', [])
                
                product = Product(
                    category_id=category.id,
                    has_sizes=category.has_sizes,
                    **{k: v for k, v in product_data.items() if k not in ['colors', 'sizes']}
                )
                db.session.add(product)
                db.session.flush()
                
                # Add sizes if specified
                if sizes:
                    total_stock = 0
                    for size in sizes:
                        size_stock = 100 // len(sizes)  # Distribute stock evenly
                        product_size = ProductSize(
                            product_id=product.id,
                            size=size,
                            stock=size_stock
                        )
                        total_stock += size_stock
                        db.session.add(product_size)
                    product.stock = total_stock
                
                # Add colors if specified
                if colors:
                    total_stock = 0
                    for color in colors:
                        product_color = ProductColor(
                            product_id=product.id,
                            color_name=color['name'],
                            color_code=color['code'],
                            stock=color['stock']
                        )
                        total_stock += color['stock']
                        db.session.add(product_color)
                    if not sizes:  # Only update stock if not using sizes
                        product.stock = total_stock
            
            print("Committing changes...")
            db.session.commit()
            print("Database initialized successfully!")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")
            raise

if __name__ == '__main__':
    init_db()