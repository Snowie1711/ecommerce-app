from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect
from extensions import db
from models import Cart, CartItem, Product, Order, OrderItem, OrderStatus
from datetime import datetime
import json
import uuid
import os
import requests

cart_bp = Blueprint('cart', __name__)
csrf = CSRFProtect()

@cart_bp.route('/cart/add/<int:product_id>', methods=['POST'])
@login_required
def add_to_cart(product_id):
    try:
        quantity = int(request.form.get('quantity', 1))
        size = request.form.get('size')
        color_id = request.form.get('color_id')
        variant_id = request.form.get('variant_id')
        
        product = Product.query.get_or_404(product_id)
        
        # Validate size if required
        if product.has_sizes and not size:
            error_msg = 'Please select a size'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('products.detail', id=product_id))

        # Validate color if required
        if product.colors and not color_id:
            error_msg = 'Please select a color'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('products.detail', id=product_id))

        # Check variant first if provided
        if variant_id:
            try:
                variant_id = int(variant_id)
                variant = next((v for v in product.variants if v.id == variant_id), None)
                if not variant:
                    error_msg = 'Selected variant not found'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('products.detail', id=product_id))
                    
                if quantity > variant.stock:
                    error_msg = 'Not enough stock available for selected variant'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('products.detail', id=product_id))
            except ValueError:
                error_msg = 'Invalid variant selected'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('products.detail', id=product_id))
        # Check size and color if no variant
        elif product.inventory_type == 'both':
            error_msg = 'Please select a size and color variant'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': error_msg}), 400
            flash(error_msg, 'error')
            return redirect(url_for('products.detail', id=product_id))
        elif size:
            size_obj = next((s for s in product.sizes if s.size == size), None)
            if not size_obj or quantity > size_obj.stock:
                error_msg = 'Not enough stock available for selected size'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('products.detail', id=product_id))
        elif color_id:
            try:
                color_id = int(color_id)
                color = next((c for c in product.colors if c.id == color_id), None)
                if not color or quantity > color.stock:
                    error_msg = 'Not enough stock available for selected color'
                    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                        return jsonify({'error': error_msg}), 400
                    flash(error_msg, 'error')
                    return redirect(url_for('products.detail', id=product_id))
            except ValueError:
                error_msg = 'Invalid color selected'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('products.detail', id=product_id))
        else:
            if quantity > product.stock:
                error_msg = 'Not enough stock available'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'error': error_msg}), 400
                flash(error_msg, 'error')
                return redirect(url_for('products.detail', id=product_id))

        # Add to cart
        # Ensure we get the correct user ID whether current_user is an object or dict
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        result = Cart.add_to_cart(user_id, product_id, quantity, size, color_id, variant_id)
        if result['success']:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Item added to cart successfully!'})
            flash('Item added to cart successfully!', 'success')
        else:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'error': result['message']}), 500
            flash(result['message'], 'error')

        return redirect(url_for('cart.view_cart'))

    except Exception as e:
        current_app.logger.error(f"Error in add_to_cart: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({'error': 'Error adding item to cart'}), 500
        flash('Error adding item to cart', 'error')
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/api/cart')
@cart_bp.route('/cart')
@login_required
def view_cart():
    try:
        # Ensure we get the correct user ID whether current_user is an object or dict
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        cart_data = Cart.get_cart_for_user(user_id)
        
        # Return JSON for API requests
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify(cart_data)
            
        # Return HTML for browser requests
        return render_template('cart/cart.html',
                           cart_items=cart_data['items'],
                           subtotal=cart_data['subtotal'],
                           shipping_cost=cart_data['shipping_cost'],
                           total=cart_data['total'])
    except Exception as e:
        current_app.logger.error(f"Error in view_cart: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.path.startswith('/api/'):
            return jsonify({'error': 'Error retrieving cart data'}), 500
        flash('Error retrieving cart data', 'error')
        return render_template('cart/cart.html',
                           cart_items=[],
                           subtotal=0,
                           shipping_cost=0,
                           total=0)

@cart_bp.route('/cart/update/<int:item_id>', methods=['POST'])
@login_required
def update_cart_item(item_id):
    try:
        # Debugging: Log headers to see what's coming in
        current_app.logger.debug("Request headers: %s", request.headers)
        
        # Check CSRF token first (will raise error if invalid/missing)
        csrf.protect()

        # Always try to parse JSON first
        try:
            data = request.get_json()
            current_app.logger.debug("Received JSON data: %s", data)
        except Exception as e:
            current_app.logger.error("Failed to parse JSON request: %s", str(e))
            return jsonify({'error': 'Invalid JSON format'}), 400

        # Validate request has JSON content type
        if not request.is_json:
            current_app.logger.error("Request content-type is not application/json")
            return jsonify({'error': 'Content-Type must be application/json'}), 400

        # Validate JSON payload exists
        if not data:
            current_app.logger.error("Empty JSON payload")
            return jsonify({'error': 'Missing JSON payload'}), 400

        # Find cart item by ID
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        item = CartItem.query.filter_by(id=item_id, user_id=user_id, deleted_at=None).first()
        
        if not item:
            current_app.logger.warning(f"Cart item {item_id} not found for user {user_id}")
            return jsonify({'error': 'Item not found in cart'}), 404

        # Validate and parse quantity
        try:
            new_quantity = int(data.get('quantity', 1))
            if new_quantity < 0:
                return jsonify({'error': 'Quantity must be non-negative'}), 400
        except (TypeError, ValueError) as e:
            current_app.logger.error(f"Invalid quantity value: {data.get('quantity')}")
            return jsonify({'error': 'Invalid quantity value'}), 400

        # Handle removing item if quantity is 0
        if new_quantity == 0:
            item.deleted_at = datetime.utcnow()  # Soft delete
            db.session.commit()
            return jsonify({
                'success': True,
                'message': 'Item removed from cart'
            })
        
        # Update quantity
        item.quantity = new_quantity
        db.session.commit()

        # Get updated cart data
        cart_data = Cart.get_cart_for_user(user_id)
        return jsonify({
            'success': True,
            'message': 'Cart updated successfully',
            'subtotal': cart_data['subtotal'],
            'total': cart_data['total']
        })

    except Exception as e:
        current_app.logger.error(f"Error updating cart: {str(e)}")
        current_app.logger.exception("Stack trace:")
        db.session.rollback()
        return jsonify({
            'error': 'Failed to update cart',
            'details': str(e)
        }), 500

@cart_bp.route('/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    try:
        # Get parameters from request form
        variant_id = request.form.get('variant_id')
        size = request.form.get('size')
        color_id = request.form.get('color_id')
        
        # Build filter conditions
        conditions = {
            'user_id': current_user.id,
            'product_id': product_id,
            'deleted_at': None
        }
        
        # Add optional parameters if they exist
        if variant_id:
            conditions['variant_id'] = variant_id
        if size:
            conditions['size'] = size
        if color_id:
            conditions['color_id'] = color_id
            
        # Find the cart item
        cart_item = CartItem.query.filter_by(**conditions).first()
        
        if cart_item:
            # Soft delete the item
            cart_item.deleted_at = datetime.utcnow()
            db.session.commit()
            message = 'Item removed from cart successfully'
            success = True
        else:
            message = 'Item not found in cart'
            success = False
            
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            return jsonify({'success': success, 'message': message})
        else:
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
            return redirect(url_for('cart.view_cart'))
            
    except Exception as e:
        # Log the error for debugging
        current_app.logger.error(f"Error removing item from cart: {str(e)}")
        
        # Check if it's an AJAX request
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        if is_ajax:
            return jsonify({'success': False, 'error': 'Error removing item from cart'}), 500
        else:
            flash('Error removing item from cart', 'error')
            return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/checkout', methods=['GET', 'POST'])
@login_required
def checkout():
    if request.method == 'POST':
        try:
            if request.is_json:
                # Parse JSON data from request
                data = request.get_json()
                shipping_info = data.get('shipping_info', {})
                payment_method = data.get('payment_method', 'cod')
                
                # Get user's cart
                user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
                cart = Cart.get_cart_for_user(user_id)
                if not cart or not cart['items']:
                    return jsonify({'success': False, 'error': 'Your cart is empty'}), 400
                
                # For PayOS payments, delete all pending payment orders first
                if payment_method == 'payos':
                    pending_orders = Order.query.filter_by(
                        user_id=user_id, 
                        status=OrderStatus.PENDING_PAYMENT
                    ).all()
                    
                    for pending_order in pending_orders:
                        db.session.delete(pending_order)
                    
                    # Commit deletions before creating new order
                    db.session.commit()
                
                # Prepare shipping address
                shipping_address = f"{shipping_info.get('address', '')}"
                if shipping_info.get('address2'):
                    shipping_address += f", {shipping_info.get('address2')}"
                shipping_address += f", {shipping_info.get('city', '')}, {shipping_info.get('state', '')}, {shipping_info.get('zip', '')}"
                
                # Create order with free shipping (total amount = subtotal)
                total_amount = cart['subtotal']  # No shipping fee added
                
                # Create new order
                order = Order(
                    user_id=user_id,
                    status=OrderStatus.PENDING_PAYMENT if payment_method == 'payos' else OrderStatus.PROCESSING,
                    total_amount=total_amount,
                    shipping_address=shipping_address,
                    billing_address=shipping_address,
                    shipping_first_name=shipping_info.get('first_name'),
                    shipping_last_name=shipping_info.get('last_name'),
                    billing_first_name=shipping_info.get('first_name'),
                    billing_last_name=shipping_info.get('last_name'),
                    payment_method=payment_method
                )
                
                db.session.add(order)
                db.session.flush()  # Get order ID without committing yet
                
                # Add items to order
                for item in cart['items']:
                    order_item = OrderItem(
                        order_id=order.id,
                        product_id=item['product_id'],
                        quantity=item['quantity'],
                        price=item['price'],
                        size=item.get('size'),
                        color_id=item.get('color_id'),
                        variant_id=item.get('variant_id')
                    )
                    db.session.add(order_item)
                
                # Process payment based on method
                if payment_method == 'payos':
                    # Handle PayOS payment
                    return process_payos_payment(order, cart, user_id)
                else:
                    # COD order, just commit and return success
                    db.session.commit()
                    
                    # Clear the cart
                    Cart.clear_cart(user_id)
                    
                    return jsonify({
                        'success': True,
                        'requires_payment': False,
                        'redirect_url': url_for('auth.purchase_history')
                    })
            else:
                # Form submission (non-AJAX)
                # Add form handling logic here if needed
                pass
                
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Checkout error: {str(e)}")
            return jsonify({'success': False, 'error': str(e)}), 500
    
    # GET request - render checkout page
    # Ensure we get the correct user ID whether current_user is an object or dict
    user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
    cart_data = Cart.get_cart_for_user(user_id)
    return render_template('cart/checkout.html',
                       cart_items=cart_data['items'],
                       subtotal=cart_data['subtotal'],
                       shipping_cost=cart_data['shipping_cost'],  # Will be 0
                       total=cart_data['total'],  # Will be same as subtotal
                       cart_item_count=len(cart_data['items']))

# Helper function to process PayOS payments
def process_payos_payment(order, cart, user_id):
    try:
        from payment_providers.payos import PayOSAPI
        payos = PayOSAPI()
        
        # Validate required parameters before calling API
        if not order.id:
            return jsonify({
                'success': False,
                'error': 'Invalid order ID'
            }), 400
            
        if not order.total_amount or order.total_amount <= 0:
            return jsonify({
                'success': False,
                'error': 'Invalid payment amount'
            }), 400
            
        # Ensure amount is an integer
        amount = int(order.total_amount)
        
        # Create payment request with the order
        payment_result = payos.create_payment(
            order_id=str(order.id),
            amount=amount,
            description=f"Order #{order.id}"
        )
        
        # Log entire payment result for debugging
        current_app.logger.info(f"PayOS payment response: {payment_result}")
        
        # Enhanced validation: Check both success and payment_url explicitly
        if payment_result.get('success') is True and payment_result.get('payment_url'):
            # Store checkout URL and commit if successful
            order.checkout_url = payment_result.get('payment_url')
            try:
                db.session.commit()
                # Clear the cart after successful order creation
                Cart.clear_cart(user_id)
                
                # Return payment URL to redirect user
                return jsonify({
                    'success': True,
                    'requires_payment': True,
                    'payment_url': order.checkout_url,  # Use stored value from order
                    'order_id': order.id
                })
            except Exception as e:
                db.session.rollback()
                current_app.logger.error(f"Failed to save order details: {str(e)}")
                return jsonify({
                    'success': False,
                    'error': 'Failed to save order details'
                }), 500
        else:
            # Payment creation failed or missing payment_url
            error_msg = "Payment initialization failed"
            
            # Get more specific error details if available
            if not payment_result.get('success'):
                error_msg = payment_result.get('error', 'Payment service returned an error')
            elif not payment_result.get('payment_url'):
                error_msg = "Payment gateway did not provide a checkout URL"
                current_app.logger.error(f"Missing payment_url in successful response: {payment_result}")
            
            # Additional error details to log
            payos_code = payment_result.get('code', 'No code')
            payos_desc = payment_result.get('desc', 'No description')
            current_app.logger.error(f"PayOS payment error: {error_msg}, Code={payos_code}, Desc={payos_desc}")
            
            # Rollback the transaction
            db.session.rollback()
            
            # Return detailed error to frontend
            return jsonify({
                'success': False,
                'error': error_msg,
                'details': f"Code: {payos_code}, Description: {payos_desc}"
            }), 400
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"PayOS payment error: {str(e)}")
        current_app.logger.exception("Full exception details:")
        return jsonify({
            'success': False,
            'error': f"Payment processing error: {str(e)}"
        }), 500