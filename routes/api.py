from flask import Blueprint, jsonify, request, current_app, session
import uuid
import json
from flask_login import login_required, current_user
from routes.auth import admin_required
from flask_wtf.csrf import validate_csrf
from werkzeug.exceptions import BadRequest
from extensions import db
from models import Product, Cart, Order, OrderStatus, ProductColor, Review, Notification, Category
from sqlalchemy.orm import joinedload
from datetime import datetime

api_bp = Blueprint('api', __name__)

def validate_api_csrf():
    try:
        token = request.headers.get('X-CSRF-Token') or request.get_json().get('csrf_token')
        if not token:
            raise BadRequest('Missing CSRF token')
        validate_csrf(token)
    except Exception as e:
        raise BadRequest('Invalid CSRF token')

def get_anonymous_user_id():
    """Get or create anonymous user identifier"""
    if 'anonymous_user_id' not in session:
        session['anonymous_user_id'] = str(uuid.uuid4())
    return session['anonymous_user_id']

@api_bp.route('/products/<int:product_id>/stock')
def get_product_stock(product_id):
    """Get available stock for a product variant"""
    try:
        product = Product.query.get_or_404(product_id)
        
        size = request.args.get('size')
        
        try:
            color_id = request.args.get('color_id')
            if color_id:
                color_id = int(color_id)
                color = next((c for c in product.colors if c.id == color_id), None)
                if color:
                    return jsonify({'stock': color.stock})
                return jsonify({'error': 'Color not found'}), 404
        except ValueError:
            return jsonify({'error': 'Invalid color ID'}), 400
            
        if size and product.has_sizes:
            size_obj = next((s for s in product.sizes if s.size == size), None)
            if size_obj:
                return jsonify({'stock': size_obj.stock})
            return jsonify({'error': 'Size not found'}), 404
                
        return jsonify({'stock': product.stock})
        
    except Exception as e:
        current_app.logger.error(f"Error getting product stock: {str(e)}")
        return jsonify({'error': 'Error getting product stock'}), 500

@api_bp.route('/products')
def get_products():
    """Get products with optional search filter"""
    try:
        search = request.args.get('search', '').strip()
        min_price = request.args.get('min_price', type=float)
        max_price = request.args.get('max_price', type=float)
        in_stock = request.args.get('in_stock')
        category = request.args.get('category')
        page = max(1, request.args.get('page', 1, type=int))
        per_page = min(50, max(1, request.args.get('per_page', 12, type=int)))

        # Base query filtering out inactive products for non-admin users
        query = Product.query
        # Check authentication and admin status safely for both dict and object current_user
        is_authenticated = getattr(current_user, 'is_authenticated', False) if not isinstance(current_user, dict) else current_user.get('is_authenticated', False)
        is_admin = getattr(current_user, 'is_admin', False) if not isinstance(current_user, dict) else current_user.get('is_admin', False)
        if not (is_authenticated and is_admin):
            query = query.filter_by(is_active=True)

        # Apply filters
        if search:
            # Split search into terms and search each term independently
            search_terms = search.split()
            for term in search_terms:
                query = query.filter(Product.name.ilike(f'%{term}%'))

        if min_price is not None:
            query = query.filter(Product.price >= min_price)
        if max_price is not None:
            query = query.filter(Product.price <= max_price)
        if in_stock is not None:
            if in_stock == '1':
                query = query.filter(Product.stock > 0)
            elif in_stock == '0':
                query = query.filter(Product.stock == 0)
        if category:
            query = query.filter(Product.category == category)

        try:
            # Try pagination first
            paginated = query.paginate(page=page, per_page=per_page)
            return jsonify({
                'success': True,
                'products': [product.to_dict() for product in paginated.items],
                'total': paginated.total,
                'pages': paginated.pages,
                'current_page': paginated.page
            })
        except Exception as e:
            # If pagination fails, return first page of results
            current_app.logger.warning(f'Pagination failed, falling back to limit: {str(e)}')
            products = query.limit(per_page).all()
            return jsonify({
                'success': True,
                'products': [product.to_dict() for product in products],
                'total': len(products),
                'pages': 1,
                'current_page': 1
            })

    except Exception as e:
        current_app.logger.error(f'Search error: {str(e)}')
        return jsonify({
            'success': False,
            'error': 'An error occurred while searching products'
        }), 500

@api_bp.route('/products/<int:id>')
def get_product(id):
    """Get a specific product"""
    # Only allow viewing active products for non-admin users
    query = Product.query
    if not (current_user.is_authenticated and current_user.is_admin):
        query = query.filter_by(is_active=True)
        
    product = query.get_or_404(id, description='Product not found or no longer available')
    
    # Check authentication and admin status safely
    is_authenticated = getattr(current_user, 'is_authenticated', False) if not isinstance(current_user, dict) else current_user.get('is_authenticated', False)
    is_admin = getattr(current_user, 'is_admin', False) if not isinstance(current_user, dict) else current_user.get('is_admin', False)
    if not product.is_active and (not is_authenticated or not is_admin):
        return jsonify({
            'error': 'Product is no longer available',
            'status': 404
        }), 404
        
    return jsonify(product.to_dict())

@api_bp.route('/cart', methods=['GET'])
def get_cart():
    """Get current user's cart"""
    try:
        # Handle both authenticated and anonymous users
        # Check authentication status safely and get appropriate user ID
        is_authenticated = getattr(current_user, 'is_authenticated', False) if not isinstance(current_user, dict) else current_user.get('is_authenticated', False)
        if is_authenticated:
            user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        else:
            user_id = get_anonymous_user_id()

        cart = Cart.get_cart_for_user(user_id)
        
        # Handle cart items safely with nested product information
        cart_data = {
            'items': [
                {
                    'id': item.get('id'),
                    'product_id': item.get('product_id'),
                    'quantity': item.get('quantity', 0),
                    'price': item.get('price', 0),
                    'subtotal': item.get('subtotal', 0),
                    'product': {
                        'name': item.get('product', {}).get('name', ''),
                        'image_url': item.get('product', {}).get('image_url', '')
                    } if item.get('product') else {}
                }
                for item in cart.get('items', [])
            ],
            'total': cart.get('total', 0)
        }
        return jsonify(cart_data)
    except Exception as e:
        current_app.logger.error(f"Error getting cart: {str(e)}")
        return jsonify({'error': str(e)}), 400

@api_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add a product to cart"""
    try:
        validate_api_csrf()  # Validate CSRF token
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        quantity = int(data.get('quantity', 1))
        size = data.get('size')
        color_id = data.get('color_id')
        
        product = Product.query.get_or_404(product_id)
        if quantity > product.stock:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        # Handle both object and dict current_user
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        result = Cart.add_to_cart(user_id, product_id, quantity, size, color_id)
        
        if result.get('success'):
            return jsonify(result), 200
        else:
            return jsonify({'error': result.get('message', 'Failed to add item to cart')}), 400
            
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        current_app.logger.error(f"Error adding to cart: {str(e)}")
        return jsonify({'error': 'An unexpected error occurred'}), 500

@api_bp.route('/cart/update/<int:product_id>', methods=['PUT'])
@login_required
def update_cart(product_id):
    """Update cart item quantity"""
    data = request.get_json()
    quantity = int(data.get('quantity', 0))
    
    if quantity < 0:
        return jsonify({'error': 'Quantity cannot be negative'}), 400
        
    product = Product.query.get_or_404(product_id)
    if quantity > product.stock:
        return jsonify({'error': 'Not enough stock available'}), 400
    
    # Handle both object and dict current_user
    user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
    result = Cart.update_quantity(user_id, product_id, quantity)
    if result:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update cart'}), 500

@api_bp.route('/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    """Remove item from cart"""
    # Handle both object and dict current_user
    user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
    if Cart.remove_from_cart(user_id, product_id):
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to remove item from cart'}), 500

@api_bp.route('/orders', methods=['POST'])
@login_required
def create_order():
    """Create a new order"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        required_fields = {
            'shipping': ['first_name', 'last_name', 'address', 'city', 'state', 'zip', 'phone'],
            'billing': ['first_name', 'last_name', 'address', 'city', 'state', 'zip']
        }

        # Validate shipping address
        shipping_address = data.get('shipping_address', {})
        missing_shipping = [field for field in required_fields['shipping'] 
                          if not shipping_address.get(field)]
        if missing_shipping:
            return jsonify({
                'error': 'Missing required shipping fields',
                'fields': missing_shipping
            }), 400

        # Only validate billing fields for online payments
        payment_method = data.get('payment_method', 'payos')
        if payment_method != 'cod':
            billing_fields = [
                'billing_first_name',
                'billing_last_name',
                'billing_address',
                'billing_city',
                'billing_state',
                'billing_zip'
            ]
            missing_billing = [field for field in billing_fields 
                             if not data.get(field)]
            if missing_billing:
                return jsonify({
                    'error': 'Missing required billing fields',
                    'fields': missing_billing
                }), 400

        # Create the order
        # Handle both object and dict current_user
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        cart = Cart.get_cart_for_user(user_id)
        if not cart or not cart.get('items'):
            return jsonify({'error': 'Cart is empty'}), 400

        cart_items = cart.get('items', [])
        total_amount = cart.get('total', 0)

        # Create new order with shipping address
        order = Order(
            user_id=user_id,  # Using already extracted user_id
            status=OrderStatus.PENDING,
            total_amount=total_amount,
            shipping_address=json.dumps({
                'first_name': shipping_address['first_name'],
                'last_name': shipping_address['last_name'],
                'address': shipping_address['address'],
                'city': shipping_address['city'],
                'state': shipping_address['state'],
                'zip': shipping_address['zip'],
                'phone': shipping_address['phone']
            }),
            billing_address=json.dumps({
                'first_name': data.get('billing_first_name', shipping_address['first_name']),
                'last_name': data.get('billing_last_name', shipping_address['last_name']),
                'address': data.get('billing_address', shipping_address['address']),
                'city': data.get('billing_city', shipping_address['city']),
                'state': data.get('billing_state', shipping_address['state']),
                'zip': data.get('billing_zip', shipping_address['zip'])
            }),
            payment_method=data.get('payment_method', 'payos'),
            created_at=datetime.utcnow()
        )

        db.session.add(order)
        db.session.flush()  # Get the order ID

        # Add order items
        for item in cart_items:
            order_item = order.add_item(
                product_id=item.get('product_id'),
                quantity=item.get('quantity', 0),
                price=item.get('price', 0)
            )
            db.session.add(order_item)

        # Only clear the cart for COD payments initially
        payment_method = data.get('payment_method', 'payos')
        if payment_method == 'cod':
            Cart.clear_cart(user_id)  # Using already extracted user_id

        db.session.commit()

        return jsonify({
            'success': True,
            'order_id': order.id,
            'total': total_amount,
            'requires_payment': payment_method != 'cod'
        })

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Order creation error: {str(e)}')
        return jsonify({'error': 'Failed to create order'}), 500

@api_bp.route('/orders/<int:order_id>')
@login_required
def get_order(order_id):
    """Get order details"""
    order = Order.query.get_or_404(order_id)
    # Handle both object and dict current_user
    user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
    if order.user_id != user_id and not getattr(current_user, 'is_admin', False):
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(order.to_dict())

@api_bp.route('/orders')
@login_required
def get_orders():
    """Get user's orders"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Admin can see all orders, users see only their own
    # Check admin status safely for both dict and object current_user
    is_admin = getattr(current_user, 'is_admin', False) if not isinstance(current_user, dict) else current_user.get('is_admin', False)
    if is_admin:
        orders = Order.query.paginate(page=page, per_page=per_page)
    else:
        # Handle both object and dict current_user
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        orders = Order.query.filter_by(user_id=user_id).paginate(
            page=page, per_page=per_page
        )
    
    return jsonify({
        'orders': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': orders.page
    })

@api_bp.route('/orders/<int:order_id>/items')
@login_required
def get_order_items(order_id):
    """Get items from a specific order with product details"""
    try:
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        items = []
        for item in order.items:
            items.append({
                'product_id': item.product.id,
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': item.price
            })

        return jsonify({
            'success': True,
            'items': items
        })

    except Exception as e:
        current_app.logger.error(f"Error getting order items: {str(e)}")
        return jsonify({'error': 'Error getting order items'}), 500

@api_bp.route('/orders/<int:order_id>/rate', methods=['POST'])
@login_required
def rate_order_products(order_id):
    """Rate multiple products from an order at once"""
    try:
        # Validate CSRF token
        validate_api_csrf()
        
        # Get the order and verify ownership
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Unauthorized'}), 403

        data = request.get_json()
        current_app.logger.info(f"Received rating data: {data}")
        if not data or 'ratings' not in data:
            return jsonify({'error': 'No rating data provided'}), 400

        order_product_ids = [item.product_id for item in order.items]
        
        # Process each rating
        for rating_data in data['ratings']:
            product_id = rating_data.get('product_id')
            rating_value = rating_data.get('rating')
            comment = rating_data.get('comment', '')

            # Validate data
            if not product_id or not rating_value:
                continue
                
            # Verify the product belongs to the order
            if product_id not in order_product_ids:
                return jsonify({'error': f'Product {product_id} does not belong to this order'}), 400
                
            # Validate rating value
            try:
                rating_value = int(rating_value)
                if not (1 <= rating_value <= 5):
                    return jsonify({'error': f'Invalid rating value: {rating_value}. Must be between 1 and 5'}), 400
            except ValueError:
                return jsonify({'error': f'Invalid rating value: {rating_value}'}), 400
                
            # Check for existing review
            existing_review = Review.query.filter_by(
                user_id=current_user.id,
                product_id=product_id
            ).first()
            
            if existing_review:
                return jsonify({'error': f'Product {product_id} has already been reviewed'}), 400

            # Create review
            review = Review(
                user_id=current_user.id,
                product_id=product_id,
                rating=rating_value,
                comment=comment
            )
            db.session.add(review)

        db.session.commit()
        return jsonify({'success': True, 'message': 'Reviews submitted successfully'})

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error submitting reviews: {str(e)}")
        return jsonify({'error': 'Failed to submit reviews'}), 500

@api_bp.route('/notifications')
@login_required
def get_notifications():
    """Get user's notifications"""
    try:
        # Get the latest 10 notifications
        notifications = Notification.query.filter_by(user_id=current_user.id)\
            .order_by(Notification.created_at.desc())\
            .limit(10)\
            .all()
            
        return jsonify({
            'notifications': [{
                'id': n.id,
                'message': n.message,
                'link': n.link,
                'is_read': n.is_read,
                'created_at': n.created_at.isoformat()
            } for n in notifications]
        })
    except Exception as e:
        current_app.logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'error': 'Error getting notifications'}), 500

@api_bp.route('/notifications/unread')
@login_required
def get_unread_count():
    """Get count of unread notifications"""
    try:
        count = Notification.query.filter_by(
            user_id=current_user.id,
            is_read=False
        ).count()
        return jsonify({'count': count})
    except Exception as e:
        current_app.logger.error(f"Error getting unread count: {str(e)}")
        return jsonify({'error': 'Error getting unread count'}), 500

@api_bp.route('/notifications/<int:notification_id>/read', methods=['POST'])
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        notification = Notification.query.get_or_404(notification_id)
        if notification.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403
            
        notification.mark_as_read()
        return jsonify({'success': True})
    except Exception as e:
        current_app.logger.error(f"Error marking notification as read: {str(e)}")
        return jsonify({'error': 'Error marking notification as read'}), 500


@api_bp.route('/admin/products')
@login_required
@admin_required
def get_admin_products():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'name')
    category = request.args.get('category')
    search = request.args.get('search', '')
    
    # Start with base query
    query = Product.query.join(Product.category).options(
        db.joinedload(Product.category),
        db.joinedload(Product.images)
    )
    
    # Apply filters
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if category:
        query = query.filter(db.func.lower(Category.name) == db.func.lower(category))
        
    # Apply sorting
    if sort == 'name':
        query = query.order_by(Product.name)
    elif sort == 'price':
        query = query.order_by(Product.price)
    elif sort == 'stock':
        query = query.order_by(Product.stock)
    elif sort == 'category':
        query = query.order_by(Category.name)
        
    # Paginate
    products = query.paginate(page=page, per_page=20)
    
    return jsonify({
        'items': [p.to_dict() for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'page': products.page
    })
@api_bp.route('/admin/products')
@login_required
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    sort = request.args.get('sort', 'name')
    category = request.args.get('category')
    search = request.args.get('search', '')
    
    # Start with base query
    query = Product.query.join(Product.category).options(
        db.joinedload(Product.category),
        db.joinedload(Product.images)
    )
    
    # Apply filters
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if category:
        query = query.filter(db.func.lower(Category.name) == db.func.lower(category))
        
    # Apply sorting
    if sort == 'name':
        query = query.order_by(Product.name)
    elif sort == 'price':
        query = query.order_by(Product.price)
    elif sort == 'stock':
        query = query.order_by(Product.stock)
    elif sort == 'category':
        query = query.order_by(Category.name)
        
    # Paginate
    products = query.paginate(page=page, per_page=20)
    
    return jsonify({
        'items': [p.to_dict() for p in products.items],
        'total': products.total,
        'pages': products.pages,
        'page': products.page
    })