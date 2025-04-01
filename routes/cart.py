from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session
from flask_login import login_required, current_user 
from flask_wtf.csrf import CSRFProtect
from models import db, Cart, Product, Order, OrderItem, OrderStatus
from datetime import datetime
import json

cart_bp = Blueprint('cart', __name__)
csrf = CSRFProtect()

@cart_bp.route('/cart')
@login_required
def view_cart():
    cart_items = Cart.get_user_cart(current_user.id)
    total = Cart.get_cart_total(current_user.id)
    return render_template('cart/cart.html', cart_items=cart_items, total=total)

@cart_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    quantity = int(request.form.get('quantity', 1))
    product = Product.query.get_or_404(product_id)
    
    if quantity > product.stock:
        flash('Not enough stock available', 'error')
        return redirect(url_for('products.detail', id=product_id))
    
    cart_item = Cart.add_to_cart(current_user.id, product_id, quantity)
    if cart_item:
        flash('Item added to cart successfully!', 'success')
    else:
        flash('Error adding item to cart', 'error')
    
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    quantity = int(request.form.get('quantity', 0))
    product = Product.query.get_or_404(product_id)
    
    if quantity > product.stock:
        flash('Not enough stock available', 'error')
        return redirect(url_for('cart.view_cart'))
    
    if Cart.update_quantity(current_user.id, product_id, quantity):
        flash('Cart updated successfully!', 'success')
    else:
        flash('Error updating cart', 'error')
    
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    if Cart.remove_from_cart(current_user.id, product_id):
        flash('Item removed from cart', 'success')
    else:
        flash('Error removing item from cart', 'error')
    
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    current_app.logger.info(f"=== Starting Checkout Process for User {current_user.id} ===")
    current_app.logger.info(f"Request Method: {request.method}")
    current_app.logger.info(f"Headers: {dict(request.headers)}")
    
    # Start transaction for cart check
    try:
        cart_items = None
        with db.session.begin_nested():
            cart_items = Cart.get_user_cart(current_user.id)
            
            if not cart_items:
                error_msg = 'Your cart is empty'
                current_app.logger.error(f"Checkout Error: {error_msg}")
                current_app.logger.error(f"Session data: {dict(session)}")
                
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('cart.view_cart'))
            
            # Log cart state at checkout
            current_app.logger.info(f"Cart validated with {len(cart_items)} items")
            for item in cart_items:
                current_app.logger.info(
                    f"Checkout item - Product: {item.product.name}, "
                    f"Quantity: {item.quantity}, "
                    f"Price: {item.product.price}"
                )
                
            # Verify cart total
            cart_total = Cart.get_cart_total(current_user.id)
            current_app.logger.info(f"Cart total at checkout: {cart_total}")
            
    except Exception as e:
        current_app.logger.error(f"Checkout error: {str(e)}")
        db.session.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': 'Error processing checkout'}), 500
        flash('Error processing checkout. Please try again.', 'error')
        return redirect(url_for('cart.view_cart'))
    
    if request.method == 'POST':
        try:
            # Get cart items and validate
            cart_items = Cart.get_user_cart(current_user.id)
            if not cart_items:
                flash('Your cart is empty', 'error')
                return redirect(url_for('cart.view_cart'))

            # Get cart total (already includes shipping if needed)
            cart_total_vnd = Cart.get_cart_total(current_user.id)
            
            # Validate amount isn't too high
            if cart_total_vnd > 100000000:  # 100M VND limit
                flash('Total amount exceeds maximum limit', 'error')
                return redirect(url_for('cart.view_cart'))

            current_app.logger.info(f"""
            Cart Details:
            - Items: {len(cart_items)}
            - Total (VND): {cart_total_vnd:,}
            """)

            # Handle JSON requests differently
            if request.is_json:
                error_context = {
                    'request_time': datetime.utcnow().isoformat(),
                    'request_id': request.headers.get('X-Request-ID', 'none')
                }
                
                try:
                    data = request.get_json()
                    if not data:
                        return jsonify({
                            'error': 'No JSON data received',
                            'status': 'validation_error'
                        }), 400
                    
                    # Log entire request data
                    current_app.logger.info('Full request data:')
                    current_app.logger.info(json.dumps(data, indent=2))

                    
                    # Update error context with request data
                    error_context.update({
                        'request_data': data,
                        'timestamp': datetime.utcnow().isoformat(),
                        'session_id': request.cookies.get('session', 'unknown')
                    })

                    current_app.logger.info(f"Received JSON data: {data}")

                    if not isinstance(data, dict):
                        raise ValueError('Invalid JSON format')
                    
                    # Log data validation steps
                    current_app.logger.info("Starting data validation...")

                    if 'shipping_info' not in data or 'payment_method' not in data:
                        raise ValueError('Missing required data: shipping_info or payment_method')

                    shipping_info = data['shipping_info']
                    payment_method = data['payment_method']
                    same_as_shipping = True

                    if not isinstance(shipping_info, dict):
                        raise ValueError('shipping_info must be an object')

                    # Validate shipping info
                    current_app.logger.info("Validating shipping info...")
                    required_fields = ['first_name', 'last_name', 'address', 'city', 'state', 'zip', 'phone']
                    for field in required_fields:
                        current_app.logger.info(f"Checking field '{field}': {shipping_info.get(field)}")
                    
                    missing_fields = [field for field in required_fields if not shipping_info.get(field)]
                    if missing_fields:
                        raise ValueError(f'Missing required fields in shipping info: {", ".join(missing_fields)}')

                    # Validate ZIP code format
                    current_app.logger.info("Validating ZIP code...")
                    zip_code = str(shipping_info.get('zip', ''))
                    current_app.logger.info(f"ZIP code value: {zip_code}")
                    # Log ZIP code details
                    current_app.logger.info(f"""
                    ZIP Code Validation Details:
                    - Raw value: {zip_code}
                    - Length: {len(zip_code)}
                    - Contains only digits: {zip_code.isdigit()}
                    - Formatted value: {zip_code.zfill(5)}
                    """)

                    if not zip_code.isdigit():
                        raise ValueError('ZIP code must contain only digits')
                    if len(zip_code) != 5:
                        raise ValueError(f'ZIP code must be exactly 5 digits (got {len(zip_code)} digits: {zip_code})')

                    # Format ZIP code to ensure 5 digits
                    zip_code = zip_code.zfill(5)
                    shipping_info['zip'] = zip_code

                    # Validate payment method
                    current_app.logger.info(f"Validating payment method: {payment_method}")
                    if payment_method not in ['payos', 'cod']:
                        raise ValueError('Invalid payment method')

                    # Validate phone number
                    current_app.logger.info("Validating phone number...")
                    phone = str(shipping_info.get('phone', ''))
                    current_app.logger.info(f"Phone number value: {phone}")
                    if not phone.isdigit():
                        raise ValueError('Phone number must contain only digits')
                    if len(phone) < 10:
                        raise ValueError('Phone number must be at least 10 digits')

                except (ValueError, Exception) as e:
                    current_app.logger.error(f"Error in JSON request: {str(e)}")
                    
                    if isinstance(e, ValueError):
                        # Handle validation errors
                        error_response = {
                            'error': str(e),
                            'status': 'validation_error',
                            'context': {
                                **error_context,
                                'validation_message': str(e),
                                'received_data': {
                                    'shipping_info': data.get('shipping_info') if 'data' in locals() else None,
                                    'payment_method': data.get('payment_method') if 'data' in locals() else None
                                }
                            }
                        }
                        status_code = 400
                    else:
                        # Handle server errors
                        error_response = {
                            'error': 'An unexpected error occurred',
                            'status': 'server_error',
                            'context': {
                                **error_context,
                                'error_details': str(e) if current_app.debug else None,
                                'error_type': e.__class__.__name__
                            }
                        }
                        status_code = 500
                        current_app.logger.exception("Full traceback:")
                    
                    current_app.logger.error(f"Error details: {json.dumps(error_response, indent=2)}")
                    db.session.rollback()
                    return jsonify(error_response), status_code

                # All validation passed, proceed with order creation
                billing_address = dict(shipping_info)
                billing_address.pop('phone', None)
                
                # Create order with appropriate status based on payment method
                order = Order(
                    user_id=current_user.id,
                    status=OrderStatus.PENDING_PAYMENT if payment_method == 'payos' else OrderStatus.PAID,
                    total_amount=cart_total_vnd,
                    shipping_address=json.dumps(shipping_info),
                    billing_address=json.dumps(billing_address),
                    payment_method=payment_method
                )
                
                db.session.add(order)
                db.session.flush()  # Get order ID

                # Add order items
                for item in cart_items:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item.product_id,
                        quantity=item.quantity,
                        price=item.product.price
                    )
                    db.session.add(order_item)
                    
                    # Only update stock for COD payments
                    if payment_method == 'cod':
                        item.product.stock -= item.quantity
                        if item.product.stock < 0:
                            raise ValueError(f'Insufficient stock for {item.product.name}')
                
                # Only clear cart for COD payments
                if payment_method == 'cod':
                    Cart.clear_cart(current_user.id)
                
                db.session.commit()

                # Return appropriate response based on payment method
                if payment_method == 'payos':
                    # Create PayOS payment
                    from routes.payment import get_payos_api
                    payos_api = get_payos_api()
                    
                    # Convert amount to integer for PayOS
                    amount_int = int(round(cart_total_vnd))
                    
                    current_app.logger.info(f"Converting amount {cart_total_vnd} to integer: {amount_int}")
                    
                    payment_result = payos_api.create_payment(
                        str(order.id),
                        amount_int,
                        f"Payment for order #{order.id}"
                    )
                    
                    if not payment_result.get('success'):
                        raise ValueError(payment_result.get('error', 'Failed to create PayOS payment'))
                    
                    order.payment_id = payment_result.get('request_id')
                    db.session.commit()

                    return jsonify({
                        'success': True,
                        'message': 'Order created and payment initialized',
                        'order_id': order.id,
                        'payment_url': payment_result.get('payment_url'),
                        'requires_payment': True
                    })
                else:
                    return jsonify({
                        'success': True,
                        'message': 'Order placed successfully!',
                        'order_id': order.id,
                        'redirect_url': url_for('auth.purchase_history')
                    })
            else:
                # Handle form data
                payment_method = request.form.get('payment_method')
                same_as_shipping = request.form.get('same_as_shipping') == 'true'

                # Validate required fields
                required_fields = ['shipping_first_name', 'shipping_last_name', 'shipping_address',
                                'shipping_city', 'shipping_state', 'shipping_zip', 'shipping_phone',
                                'payment_method']
                
                # Only require billing info when not same as shipping
                if not same_as_shipping:
                    required_fields.extend([
                        'billing_first_name', 'billing_last_name', 'billing_address',
                        'billing_city', 'billing_state', 'billing_zip'
                    ])
            
            # Validate required fields
            missing_fields = [field for field in required_fields if not request.form.get(field)]
            if missing_fields:
                error_msg = f'Missing required fields: {", ".join(missing_fields)}'
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('cart.checkout'))

            # Validate ZIP code formats
            if not request.form['shipping_zip'].isdigit() or len(request.form['shipping_zip']) != 5:
                error_msg = 'Invalid shipping ZIP code format (must be 5 digits)'
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('cart.checkout'))

            if not same_as_shipping:
                if not request.form['billing_zip'].isdigit() or len(request.form['billing_zip']) != 5:
                    error_msg = 'Invalid billing ZIP code format (must be 5 digits)'
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('cart.checkout'))

            # Validate stock availability
            for item in cart_items:
                if item.quantity > item.product.stock:
                    error_msg = f'Not enough stock available for {item.product.name}'
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('cart.view_cart'))
            
            if not request.is_json:
                # Prepare shipping address from form data
                shipping_address = {
                    'first_name': request.form['shipping_first_name'],
                    'last_name': request.form['shipping_last_name'],
                    'address': request.form['shipping_address'],
                    'city': request.form['shipping_city'],
                    'state': request.form['shipping_state'],
                    'zip': request.form['shipping_zip'],
                    'phone': request.form['shipping_phone']
                }
                
                # Prepare billing address from form data
                if same_as_shipping:
                    billing_address = dict(shipping_address)  # Create a copy of shipping address
                    billing_address.pop('phone', None)  # Remove phone as it's not needed for billing
                else:
                    billing_address = {
                        'first_name': request.form['billing_first_name'],
                        'last_name': request.form['billing_last_name'],
                        'address': request.form['billing_address'],
                        'city': request.form['billing_city'],
                        'state': request.form['billing_state'],
                        'zip': request.form['billing_zip']
                    }
                    
                # Validate ZIP code formats for form data
                if not shipping_address['zip'].isdigit() or len(shipping_address['zip']) != 5:
                    error_msg = 'Invalid shipping ZIP code format (must be 5 digits)'
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('cart.checkout'))

                if not same_as_shipping and (not billing_address['zip'].isdigit() or len(billing_address['zip']) != 5):
                    error_msg = 'Invalid billing ZIP code format (must be 5 digits)'
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('cart.checkout'))

            # Create order with appropriate status based on payment method
            order = Order(
                user_id=current_user.id,
                status=OrderStatus.PENDING_PAYMENT if payment_method == 'payos' else OrderStatus.PAID,
                total_amount=cart_total_vnd,  # Use the calculated VND amount
                shipping_address=json.dumps(shipping_address),
                billing_address=json.dumps(billing_address),
                payment_method=payment_method
            )
            
            db.session.add(order)
            db.session.flush()  # Get the order ID without committing
            
            # Add order items but don't update stock yet for PayOS
            for item in cart_items:
                order_item = OrderItem(
                    order_id=order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    price=item.product.price
                )
                db.session.add(order_item)
                
                # Only update stock for COD payments
                if payment_method == 'cod':
                    item.product.stock -= item.quantity
                    if item.product.stock < 0:
                        raise ValueError(f'Insufficient stock for {item.product.name}')
            
            # Only clear cart for COD payments
            if payment_method == 'cod':
                Cart.clear_cart(current_user.id)
            
            db.session.commit()

            # Handle response based on payment method
            if payment_method == 'payos':
                # Create PayOS payment
                try:
                    # Get PayOS API instance
                    from routes.payment import get_payos_api
                    payos_api = get_payos_api()

                    current_app.logger.info(f"""
                    Creating PayOS payment:
                    - Order ID: {order.id}
                    - Amount (VND): {cart_total_vnd:,}
                    """)
                    
                    # Convert amount to integer for PayOS
                    amount_int = int(round(cart_total_vnd))
                    
                    current_app.logger.info(f"Converting amount {cart_total_vnd} to integer: {amount_int}")
                    
                    payment_result = payos_api.create_payment(
                        str(order.id),
                        amount_int,
                        f"Payment for order #{order.id}"
                    )
                    
                    current_app.logger.info(f"PayOS payment result: {payment_result}")
                    
                    if not payment_result.get('success'):
                        raise ValueError(payment_result.get('error', 'Failed to create PayOS payment'))
                    
                    # Update order with payment information
                    order.payment_id = payment_result.get('request_id')
                    db.session.commit()
                    
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({
                            'success': True,
                            'message': 'Order created and payment initialized',
                            'order_id': order.id,
                            'payment_url': payment_result.get('payment_url'),
                            'requires_payment': True
                        })
                        
                    # Redirect to PayOS payment page
                    return redirect(payment_result.get('payment_url'))
                except Exception as e:
                    current_app.logger.error(f'PayOS payment creation failed: {str(e)}')
                    db.session.rollback()
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({
                            'error': 'Failed to initialize PayOS payment',
                            'details': str(e)
                        }), 500
                    flash('Payment initialization failed. Please try again.', 'error')
                    return redirect(url_for('cart.checkout'))
            else:
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'success': True,
                        'message': 'Order placed successfully!',
                        'redirect_url': url_for('auth.purchase_history')
                    })
                flash('Order placed successfully!', 'success')
                return redirect(url_for('auth.purchase_history'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Detailed checkout error: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            
            if isinstance(e, ValueError):
                error_msg = str(e)
            else:
                error_msg = 'An unexpected error occurred. Please try again.'
                
            current_app.logger.error(f"Cart total VND: {cart_total_vnd}")
            current_app.logger.error(f"Form data: {request.form}")
            
            db.session.rollback()
            
            if request.headers.get('Accept') == 'application/json':
                error_details = {'total': cart_total_vnd}
                if 'payment_method' in locals():
                    error_details['payment_method'] = payment_method
                return jsonify({
                    'error': error_msg,
                    'details': error_details
                }), 500
            
            flash(error_msg, 'error')
            return redirect(url_for('cart.checkout'))
    
    # Get cart total (already includes shipping from Cart.get_cart_total)
    cart_total_vnd = Cart.get_cart_total(current_user.id)
    return render_template('cart/checkout.html', cart_items=cart_items, total=cart_total_vnd)

# API endpoints
@cart_bp.route('/api/cart')
@login_required
def api_get_cart():
    cart_items = Cart.get_user_cart(current_user.id)
    if not cart_items:
        return jsonify({
            'error': 'Cart is empty',
            'items': [],
            'total': 0
        }), 400
    
    return jsonify({
        'items': [item.to_dict() for item in cart_items],
        'total': Cart.get_cart_total(current_user.id)
    })

@cart_bp.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def api_add_to_cart(product_id):
    data = request.get_json()
    quantity = int(data.get('quantity', 1))
    
    product = Product.query.get_or_404(product_id)
    if quantity > product.stock:
        return jsonify({'error': 'Not enough stock available'}), 400
    
    cart_item = Cart.add_to_cart(current_user.id, product_id, quantity)
    if cart_item:
        return jsonify(cart_item.to_dict()), 201
    return jsonify({'error': 'Error adding item to cart'}), 500

@cart_bp.route('/api/cart/update/<int:product_id>', methods=['PUT'])
@login_required
def api_update_cart(product_id):
    data = request.get_json()
    quantity = int(data.get('quantity', 0))
    
    product = Product.query.get_or_404(product_id)
    if quantity > product.stock:
        return jsonify({'error': 'Not enough stock available'}), 400
    
    cart_item = Cart.update_quantity(current_user.id, product_id, quantity)
    if cart_item:
        return jsonify(cart_item.to_dict())
    return jsonify({'error': 'Error updating cart'}), 500

@cart_bp.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def api_remove_from_cart(product_id):
    if Cart.remove_from_cart(current_user.id, product_id):
        return '', 204
    return jsonify({'error': 'Error removing item from cart'}), 500

@cart_bp.route('/api/cart/clear', methods=['POST'])
@login_required
def api_clear_cart():
    if Cart.clear_cart(current_user.id):
        return '', 204
    return jsonify({'error': 'Error clearing cart'}), 500

@cart_bp.route('/cart/get-items', methods=['GET'])
@login_required
def get_cart_items():
    cart_items = Cart.get_user_cart(current_user.id)
    if not cart_items:
        return jsonify({
            'items': [],
            'total': 0
        })
    
    cart_total = Cart.get_cart_total(current_user.id)
    return jsonify({
        'items': [item.to_dict() for item in cart_items],
        'total': int(round(cart_total))  # Ensure consistent integer amounts for VND
    })