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
    cart_totals = Cart.get_cart_total(current_user.id)
    return render_template('cart/cart.html',
                         cart_items=cart_items,
                         subtotal=cart_totals['subtotal'],
                         shipping_cost=cart_totals['shipping_cost'],
                         total=cart_totals['total'])

@cart_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    current_app.logger.info(f"=== Adding item to cart for User {current_user.id} ===")
    current_app.logger.info(f"Product ID: {product_id}")
    
    try:
        quantity = int(request.form.get('quantity', 1))
        current_app.logger.info(f"Requested quantity: {quantity}")
        
        product = Product.query.get_or_404(product_id)
        current_app.logger.info(f"Found product: {product.name}, Stock: {product.stock}")
        
        if quantity > product.stock:
            error_msg = 'Not enough stock available'
            current_app.logger.warning(f"Stock error: {error_msg}")
            flash(error_msg, 'error')
            return redirect(url_for('products.detail', id=product_id))
        
        # Add to cart
        cart_item = Cart.add_to_cart(current_user.id, product_id, quantity)
        
        if cart_item:
            current_app.logger.info(f"Successfully added item to cart. Cart item ID: {cart_item.id}")
            flash('Item added to cart successfully!', 'success')
        else:
            current_app.logger.error("Failed to add item to cart")
            flash('Error adding item to cart', 'error')
        
        return redirect(url_for('cart.view_cart'))
        
    except Exception as e:
        current_app.logger.error(f"Error in add_to_cart: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
        flash('Error adding item to cart', 'error')
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    if Cart.remove_from_cart(current_user.id, product_id):
        flash('Item removed from cart', 'success')
    else:
        flash('Error removing item from cart', 'error')
    return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    try:
        quantity = int(request.form.get('quantity', 0))
        product = Product.query.get_or_404(product_id)
        
        if quantity > product.stock:
            flash('Not enough stock available', 'error')
            return redirect(url_for('cart.view_cart'))
        
        if quantity > 0:
            if Cart.update_quantity(current_user.id, product_id, quantity):
                flash('Cart updated successfully!', 'success')
            else:
                flash('Error updating cart', 'error')
        else:
            if Cart.remove_from_cart(current_user.id, product_id):
                flash('Item removed from cart', 'success')
            else:
                flash('Error removing item from cart', 'error')
        
        return redirect(url_for('cart.view_cart'))
        
    except ValueError:
        flash('Invalid quantity', 'error')
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    current_app.logger.info(f"=== Starting Checkout Process for User {current_user.id} ===")
    current_app.logger.info(f"Request Method: {request.method}")
    
    # Get cart items and verify they're valid for checkout
    cart_items = Cart.get_user_cart(current_user.id)
    current_app.logger.info(f"Processing checkout with {len(cart_items) if cart_items else 0} items")
    
    # Validate cart has items and they have stock
    if not cart_items:
        error_msg = 'Your cart is empty'
        current_app.logger.error(f"Checkout Error: {error_msg}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('cart.view_cart'))
        
    # Check if any items are out of stock
    invalid_items = [item for item in cart_items if not item.product or item.product.stock <= 0]
    if invalid_items:
        error_msg = 'Some items in your cart are no longer available'
        current_app.logger.error(f"Checkout Error: {error_msg}")
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': error_msg}), 400
        flash(error_msg, 'error')
        return redirect(url_for('cart.view_cart'))
        
    # Get cart totals
    cart_totals = Cart.get_cart_total(current_user.id)
    cart_total_vnd = cart_totals['total']
    
    # Handle GET request
    if request.method == 'GET':
        return render_template('cart/checkout.html',
                           cart_items=cart_items,
                           subtotal=cart_totals['subtotal'],
                           shipping_cost=cart_totals['shipping_cost'],
                           total=cart_total_vnd)
    
    # Handle POST request
    try:
        # Get JSON data if present
        if request.is_json:
            data = request.get_json()
            if not data:
                return jsonify({
                    'error': 'No JSON data received',
                    'status': 'validation_error'
                }), 400
            shipping_info = data.get('shipping_info')
            payment_method = data.get('payment_method')
        else:
            # Get form data
            shipping_info = {
                'first_name': request.form['shipping_first_name'],
                'last_name': request.form['shipping_last_name'],
                'address': request.form['shipping_address'],
                'city': request.form['shipping_city'],
                'state': request.form['shipping_state'],
                'zip': request.form['shipping_zip'],
                'phone': request.form['shipping_phone']
            }
            payment_method = request.form.get('payment_method')

        # Validate required data
        if not shipping_info or not payment_method:
            error_msg = 'Missing required information'
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('cart.checkout'))

        # Create and validate order
        try:
            order = Order(
                user_id=current_user.id,
                status=OrderStatus.PENDING_PAYMENT if payment_method == 'payos' else OrderStatus.PAID,
                total_amount=cart_total_vnd,
                shipping_address=json.dumps(shipping_info),
                billing_address=json.dumps(shipping_info),
                payment_method=payment_method
            )
            
            db.session.add(order)
            db.session.flush()
            
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
                    if item.quantity > item.product.stock:
                        raise ValueError(f'Insufficient stock for {item.product.name}')
                    item.product.stock -= item.quantity
            
            # Handle payment method
            if payment_method == 'payos':
                try:
                    # Create PayOS payment
                    payment_result = handle_payos_payment(order, cart_total_vnd)
                    
                    # Clear cart only after successful payment creation
                    Cart.clear_cart(current_user.id)
                    db.session.commit()
                    
                    return jsonify({
                        'success': True,
                        'message': 'Payment initialized',
                        'payment_url': payment_result.get('payment_url'),
                        'requires_payment': True,
                        'order_id': order.id
                    })
                    
                except ValueError as e:
                    # If PayOS fails, suggest COD
                    db.session.rollback()
                    error_msg = str(e)
                    if request.headers.get('Accept') == 'application/json':
                        return jsonify({
                            'error': error_msg,
                            'suggest_cod': True
                        }), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('cart.checkout'))
            else:
                # Handle COD payment
                Cart.clear_cart(current_user.id)
                db.session.commit()
                
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({
                        'success': True,
                        'message': 'Order placed successfully!',
                        'redirect_url': url_for('auth.purchase_history')
                    })
                    
                flash('Order placed successfully!', 'success')
                return redirect(url_for('auth.purchase_history'))
                
        except ValueError as e:
            db.session.rollback()
            error_msg = str(e)
            if request.headers.get('Accept') == 'application/json':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('cart.checkout'))
            
    except Exception as e:
        current_app.logger.error(f"Checkout error: {str(e)}")
        db.session.rollback()
        error_msg = str(e) if isinstance(e, ValueError) else 'Error processing checkout'
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'error': error_msg}), 500
        flash(error_msg, 'error')
        return redirect(url_for('cart.checkout'))

def handle_payos_payment(order, amount):
    """Handle PayOS payment creation with proper error handling"""
    try:
        from routes.payment import get_payos_api
        
        # Get PayOS API instance
        payos_api = get_payos_api()
        if not payos_api:
            current_app.logger.warning("PayOS API not configured properly")
            raise ValueError(
                'Online payment is not available at this time. '
                'Please choose COD payment method instead.'
            )
            
        # Prepare payment amount
        try:
            amount_int = int(round(amount))
        except (TypeError, ValueError):
            current_app.logger.error(f"Invalid payment amount: {amount}")
            raise ValueError('Invalid payment amount')
            
        # Create payment
        try:
            payment_result = payos_api.create_payment(
                str(order.id),
                amount_int,
                f"Payment for order #{order.id}"
            )
        except Exception as e:
            current_app.logger.error(f"PayOS payment creation failed: {str(e)}")
            raise ValueError(
                'Unable to create payment at this time. '
                'Please try COD payment method instead.'
            )
            
        # Validate payment result
        if not payment_result.get('success'):
            error_msg = payment_result.get('error', 'Unknown error')
            current_app.logger.error(f"PayOS payment failed: {error_msg}")
            raise ValueError(
                'Payment initialization failed. '
                'Please try COD payment method instead.'
            )
            
        # Update order with payment info
        try:
            order.payment_id = payment_result.get('request_id')
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Failed to update order payment info: {str(e)}")
            db.session.rollback()
            raise ValueError('Error updating order payment information')
            
        return payment_result
        
    except ImportError as e:
        current_app.logger.error(f"PayOS module import failed: {str(e)}")
        raise ValueError(
            'Online payment system is currently unavailable. '
            'Please choose COD payment method.'
        )
        
    except Exception as e:
        current_app.logger.error(f"PayOS payment handling error: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
        if current_app.debug:
            error_msg = str(e)
        else:
            error_msg = (
                'Online payment is currently unavailable. '
                'Please choose COD payment method instead.'
            )
        raise ValueError(error_msg)

@cart_bp.route('/api/cart')
@login_required
def api_get_cart():
    current_app.logger.info(f"=== API Get Cart for User {current_user.id} ===")
    
    try:
        cart_items = Cart.get_user_cart(current_user.id)
        current_app.logger.info(f"Retrieved {len(cart_items) if cart_items else 0} cart items")
        
        cart_totals = Cart.get_cart_total(current_user.id)
        current_app.logger.info(f"Cart totals: {cart_totals}")
        
        total_items = sum(item.quantity for item in cart_items) if cart_items else 0
        current_app.logger.info(f"Total items in cart: {total_items}")
        
        return jsonify({
            'items': [item.to_dict() for item in cart_items] if cart_items else [],
            'subtotal': cart_totals['subtotal'],
            'shipping_cost': cart_totals['shipping_cost'],
            'total': cart_totals['total'],
            'total_items': total_items
        })
        
    except Exception as e:
        current_app.logger.error(f"Error retrieving cart data: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
        return jsonify({
            'items': [],
            'subtotal': 0,
            'shipping_cost': 0,
            'total': 0,
            'total_items': 0
        })

@cart_bp.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required
def api_add_to_cart(product_id):
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 1))
        
        product = Product.query.get_or_404(product_id)
        if quantity > product.stock:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        cart_item = Cart.add_to_cart(current_user.id, product_id, quantity)
        if cart_item:
            return jsonify(cart_item.to_dict()), 201
        return jsonify({'error': 'Error adding item to cart'}), 500
        
    except Exception as e:
        current_app.logger.error(f"API add to cart error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/api/cart/update/<int:product_id>', methods=['PUT'])
@login_required
def api_update_cart(product_id):
    try:
        data = request.get_json()
        quantity = int(data.get('quantity', 0))
        
        if quantity <= 0:
            if Cart.remove_from_cart(current_user.id, product_id):
                return '', 204
            return jsonify({'error': 'Error removing item'}), 500
        
        product = Product.query.get_or_404(product_id)
        if quantity > product.stock:
            return jsonify({'error': 'Not enough stock available'}), 400
        
        cart_item = Cart.update_quantity(current_user.id, product_id, quantity)
        if cart_item:
            return jsonify(cart_item.to_dict())
        return jsonify({'error': 'Error updating cart'}), 500
        
    except Exception as e:
        current_app.logger.error(f"API update cart error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required
def api_remove_from_cart(product_id):
    try:
        if Cart.remove_from_cart(current_user.id, product_id):
            return '', 204
        return jsonify({'error': 'Error removing item from cart'}), 500
        
    except Exception as e:
        current_app.logger.error(f"API remove from cart error: {str(e)}")
        return jsonify({'error': str(e)}), 500

@cart_bp.route('/api/cart/clear', methods=['POST'])
@login_required
def api_clear_cart():
    try:
        if Cart.clear_cart(current_user.id):
            return '', 204
        return jsonify({'error': 'Error clearing cart'}), 500
        
    except Exception as e:
        current_app.logger.error(f"API clear cart error: {str(e)}")
        return jsonify({'error': str(e)}), 500