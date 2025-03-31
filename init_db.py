#!/usr/bin/env python
from app import create_app
from models import db, User, Product, Order, OrderItem, OrderStatus, Category, ProductImage
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random
import json

def backup_orders():
    """Backup existing orders before schema change"""
    app = create_app('development')
    with app.app_context():
        orders = []
        try:
            # Get all orders and their relationships
            for order in Order.query.all():
                order_data = {
                    'id': order.id,
                    'user_id': order.user_id,
                    'status': order.status.value,
                    'total_amount': order.total_amount,
                    'shipping_address': order.shipping_address,
                    'billing_address': order.billing_address,  # Old format
                    'payment_method': order.payment_method,
                    'payment_id': order.payment_id,
                    'tracking_number': order.tracking_number,
                    'notes': order.notes,
                    'created_at': order.created_at,
                    'updated_at': order.updated_at,
                    'items': []
                }
                # Backup order items
                for item in order.items:
                    order_data['items'].append({
                        'product_id': item.product_id,
                        'quantity': item.quantity,
                        'price': item.price
                    })
                orders.append(order_data)
            return orders
        except Exception as e:
            print(f"Error backing up orders: {e}")
            return []

def restore_orders(orders_backup):
    """Restore orders with new schema"""
    app = create_app('development')
    with app.app_context():
        try:
            for order_data in orders_backup:
                # Parse billing address from old format if it exists
                old_billing = {}
                if order_data.get('billing_address'):
                    try:
                        old_billing = json.loads(order_data['billing_address'])
                    except:
                        pass

                # Create order with new schema
                order = Order(
                    user_id=order_data['user_id'],
                    status=OrderStatus.from_string(order_data['status']),
                    total_amount=order_data['total_amount'],
                    shipping_address=order_data['shipping_address'],
                    # Set billing fields from old data if available
                    billing_first_name=old_billing.get('first_name', ''),
                    billing_last_name=old_billing.get('last_name', ''),
                    billing_address=old_billing.get('address', ''),
                    billing_city=old_billing.get('city', ''),
                    billing_state=old_billing.get('state', ''),
                    billing_zip=old_billing.get('zip', ''),
                    payment_method=order_data['payment_method'],
                    payment_id=order_data['payment_id'],
                    tracking_number=order_data['tracking_number'],
                    notes=order_data['notes'],
                    created_at=order_data['created_at'],
                    updated_at=order_data['updated_at']
                )
                db.session.add(order)
                db.session.flush()  # Get order ID

                # Restore order items
                for item_data in order_data['items']:
                    item = OrderItem(
                        order_id=order.id,
                        product_id=item_data['product_id'],
                        quantity=item_data['quantity'],
                        price=item_data['price']
                    )
                    db.session.add(item)
            
            db.session.commit()
            print("Orders restored successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error restoring orders: {e}")

def init_db():
    app = create_app('development')
    
    with app.app_context():
        # Backup existing orders
        orders_backup = backup_orders()
        
        # Drop existing tables
        db.drop_all()
        
        # Create all tables with new schema
        db.create_all()
        
        # Create admin user if it doesn't exist
        if not User.query.filter_by(email='admin@example.com').first():
            admin = User(
                email='admin@example.com',
                username='admin',
                password='admin123',  # Will be hashed by the model
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            db.session.add(admin)
        
        # Create test user if it doesn't exist
        if not User.query.filter_by(email='user@example.com').first():
            user = User(
                email='user@example.com',
                username='testuser',
                password='test123',  # Will be hashed by the model
                first_name='Test',
                last_name='User'
            )
            db.session.add(user)
        
        # Create categories
        categories = {
            'Electronics': 'Electronic devices and accessories',
            'Sports & Outdoors': 'Sports equipment and outdoor gear',
            'Home & Kitchen': 'Home appliances and kitchen essentials',
            'Clothing': 'Apparel and fashion accessories',
            'Books': 'Books and publications'
        }
        
        category_objects = {}
        for name, description in categories.items():
            slug = name.lower().replace(' & ', '-').replace(' ', '-')
            category = Category(
                name=name,
                slug=slug,
                description=description
            )
            db.session.add(category)
            db.session.flush()  # Get category ID
            category_objects[name] = category
        
        # Sample product data with at least 7 products per category
        sample_products = [
            # Electronics
            {
                'name': 'Smartphone X Pro',
                'description': 'Latest flagship smartphone with advanced features',
                'price': 999.99,
                'stock': 50,
                'sku': 'PHONE-001',
                'category_id': lambda: category_objects['Electronics'].id,
                'images': ['20250326_110208_images.jpg']
            },
            {
                'name': 'Laptop Ultra',
                'description': 'Powerful laptop for professionals',
                'price': 1299.99,
                'stock': 30,
                'sku': 'LAPTOP-001',
                'category_id': lambda: category_objects['Electronics'].id
            },
            {
                'name': 'Wireless Earbuds',
                'description': 'High-quality wireless earbuds with noise cancellation',
                'price': 199.99,
                'stock': 100,
                'sku': 'AUDIO-001',
                'category_id': lambda: category_objects['Electronics'].id
            },
            # Sports & Outdoors
            {
                'name': 'Mountain Bike Pro',
                'description': 'Professional mountain bike for advanced riders',
                'price': 899.99,
                'stock': 15,
                'sku': 'BIKE-001',
                'category_id': lambda: category_objects['Sports & Outdoors'].id
            },
            {
                'name': 'Yoga Mat Premium',
                'description': 'Extra thick yoga mat with carrying strap',
                'price': 49.99,
                'stock': 200,
                'sku': 'YOGA-001',
                'category_id': lambda: category_objects['Sports & Outdoors'].id
            },
            {
                'name': 'Tennis Racket Elite',
                'description': 'Professional tennis racket',
                'price': 159.99,
                'stock': 40,
                'sku': 'TENNIS-001',
                'category_id': lambda: category_objects['Sports & Outdoors'].id
            },
            # Home & Kitchen
            {
                'name': 'Coffee Maker Deluxe',
                'description': 'Programmable coffee maker with thermal carafe',
                'price': 129.99,
                'stock': 75,
                'sku': 'COFFEE-001',
                'category_id': lambda: category_objects['Home & Kitchen'].id,
                'images': ['20250326_122247_images.jpg']
            },
            {
                'name': 'Stand Mixer Pro',
                'description': 'Professional stand mixer for baking',
                'price': 299.99,
                'stock': 25,
                'sku': 'MIXER-001',
                'category_id': lambda: category_objects['Home & Kitchen'].id
            },
            {
                'name': 'Smart Toaster',
                'description': 'Digital toaster with multiple settings',
                'price': 79.99,
                'stock': 60,
                'sku': 'TOAST-001',
                'category_id': lambda: category_objects['Home & Kitchen'].id
            },
            # Clothing
            {
                'name': 'Winter Jacket',
                'description': 'Warm winter jacket with water-resistant coating',
                'price': 199.99,
                'stock': 80,
                'sku': 'JACKET-001',
                'category_id': lambda: category_objects['Clothing'].id
            },
            {
                'name': 'Running Shoes',
                'description': 'Lightweight running shoes with cushioning',
                'price': 129.99,
                'stock': 100,
                'sku': 'SHOES-001',
                'category_id': lambda: category_objects['Clothing'].id
            },
            {
                'name': 'Cotton T-Shirt',
                'description': 'Premium cotton t-shirt',
                'price': 24.99,
                'stock': 200,
                'sku': 'TSHIRT-001',
                'category_id': lambda: category_objects['Clothing'].id
            },
            # Books
            {
                'name': 'Python Programming Guide',
                'description': 'Comprehensive guide to Python programming',
                'price': 49.99,
                'stock': 150,
                'sku': 'BOOK-001',
                'category_id': lambda: category_objects['Books'].id
            },
            {
                'name': 'Cooking Masterclass',
                'description': 'Professional cooking techniques and recipes',
                'price': 39.99,
                'stock': 120,
                'sku': 'BOOK-002',
                'category_id': lambda: category_objects['Books'].id
            },
            {
                'name': 'Science Fiction Collection',
                'description': 'Collection of classic science fiction stories',
                'price': 29.99,
                'stock': 90,
                'sku': 'BOOK-003',
                'category_id': lambda: category_objects['Books'].id
            }
        ]
        
        # Add sample products if they don't exist
        for product_data in sample_products:
            if not Product.query.filter_by(sku=product_data['sku']).first():
                # Extract images before creating product
                images = product_data.pop('images', [])
                
                # Resolve category_id lambda
                category_id = product_data['category_id']()
                product_data['category_id'] = category_id
                
                # Create product
                product = Product(**product_data)
                db.session.add(product)
                db.session.flush()  # Get product ID
                
                # Add images if any
                for i, image_name in enumerate(images):
                    product_image = ProductImage(
                        product_id=product.id,
                        image_url=image_name,
                        is_primary=(i == 0)  # First image is primary
                    )
                    db.session.add(product_image)
        
        # Create sample orders
        user = User.query.filter_by(email='user@example.com').first()
        if user and not Order.query.filter_by(user_id=user.id).first():
            products = Product.query.all()
            
            # Create orders over the last 30 days
            for i in range(5):
                order_date = datetime.utcnow() - timedelta(days=random.randint(1, 30))
                
                # Create sample addresses
                shipping_address = {
                    'first_name': 'Test',
                    'last_name': 'User',
                    'address': '123 Test St',
                    'city': 'Test City',
                    'state': 'TS',
                    'zip': '12345',
                    'phone': '555-0123'
                }

                # Create order with new schema
                order = Order(
                    user_id=user.id,
                    status=random.choice(list(OrderStatus)),
                    total_amount=0,
                    shipping_address=json.dumps(shipping_address),
                    billing_first_name='Test',
                    billing_last_name='User',
                    billing_address='123 Test St',
                    billing_city='Test City',
                    billing_state='TS',
                    billing_zip='12345',
                    payment_method='credit_card',
                    created_at=order_date
                )
                db.session.add(order)
                db.session.flush()  # Get order ID
                
                # Add 1-3 random products to each order
                order_total = 0
                for _ in range(random.randint(1, 3)):
                    product = random.choice(products)
                    quantity = random.randint(1, 3)
                    
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=product.id,
                        quantity=quantity,
                        price=product.price
                    )
                    order_total += product.price * quantity
                    db.session.add(order_item)
                
                order.total_amount = order_total
        
        # Restore backed up orders with new schema
        restore_orders(orders_backup)
        
        try:
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")

if __name__ == '__main__':
    init_db()