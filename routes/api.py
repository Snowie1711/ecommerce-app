from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from models import db, Product, Cart, Order, OrderStatus
from datetime import datetime
import json

api_bp = Blueprint('api', __name__)

@api_bp.route('/products')
def get_products():
    """Get products with optional search filter"""
    search = request.args.get('search', '')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock', type=bool)
    category = request.args.get('category')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 12, type=int)

    # Base query filtering out inactive products for non-admin users
    query = Product.query
    if not (current_user.is_authenticated and current_user.is_admin):
        query = query.filter_by(is_active=True)

    # Apply filters
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock:
        query = query.filter(Product.stock > 0)
    if category:
        query = query.filter(Product.category == category)

    # Paginate results
    paginated = query.paginate(page=page, per_page=per_page)

    return jsonify({
        'success': True,
        'products': [product.to_dict() for product in paginated.items],
        'total': paginated.total,
        'pages': paginated.pages,
        'current_page': paginated.page
    })

@api_bp.route('/products/<int:id>')
def get_product(id):
    """Get a specific product"""
    # Only allow viewing active products for non-admin users
    query = Product.query
    if not (current_user.is_authenticated and current_user.is_admin):
        query = query.filter_by(is_active=True)
        
    product = query.get_or_404(id, description='Product not found or no longer available')
    
    # Check if product is active for non-admin users
    if not product.is_active and (not current_user.is_authenticated or not current_user.is_admin):
        return jsonify({
            'error': 'Product is no longer available',
            'status': 404
        }), 404
        
    return jsonify(product.to_dict())


@api_bp.route('/cart')
@login_required
def get_cart():
    """Get the current user's cart"""
    cart_items = Cart.get_user_cart(current_user.id)
    return jsonify({
        'items': [item.to_dict() for item in cart_items],
        'total': Cart.get_cart_total(current_user.id)
    })

@api_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    """Add a product to cart"""
    data = request.get_json()
    quantity = int(data.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    if quantity > product.stock:
        return jsonify({'error': 'Not enough stock available'}), 400
    
    cart_item = Cart.add_to_cart(current_user.id, product_id, quantity)
    if cart_item:
        return jsonify(cart_item.to_dict())
    return jsonify({'error': 'Failed to add item to cart'}), 500

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
    
    result = Cart.update_quantity(current_user.id, product_id, quantity)
    if result:
        return jsonify({'success': True})
    return jsonify({'error': 'Failed to update cart'}), 500

@api_bp.route('/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def remove_from_cart(product_id):
    """Remove item from cart"""
    if Cart.remove_from_cart(current_user.id, product_id):
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
        cart_items = Cart.get_user_cart(current_user.id)
        if not cart_items:
            return jsonify({'error': 'Cart is empty'}), 400

        total_amount = sum(item.subtotal for item in cart_items)

        # Create new order with shipping address
        order = Order(
            user_id=current_user.id,
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
            # Use shipping address as billing if same_as_shipping is true
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
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.product.price
            )
            db.session.add(order_item)

        # Only clear the cart for COD payments initially
        payment_method = data.get('payment_method', 'payos')
        if payment_method == 'cod':
            Cart.clear_cart(current_user.id)

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
    if order.user_id != current_user.id and not current_user.is_admin:
        return jsonify({'error': 'Unauthorized'}), 403
    return jsonify(order.to_dict())

@api_bp.route('/orders')
@login_required
def get_orders():
    """Get user's orders"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    
    # Admin can see all orders, users see only their own
    if current_user.is_admin:
        orders = Order.query.paginate(page=page, per_page=per_page)
    else:
        orders = Order.query.filter_by(user_id=current_user.id).paginate(
            page=page, per_page=per_page
        )
    
    return jsonify({
        'orders': [order.to_dict() for order in orders.items],
        'total': orders.total,
        'pages': orders.pages,
        'current_page': orders.page
    })