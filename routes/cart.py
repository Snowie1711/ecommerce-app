from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, session, current_app
from flask_login import login_required, current_user
from flask_wtf.csrf import CSRFProtect
from models import db, Cart, CartItem, Product, Order, OrderItem, OrderStatus
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

        # Check stock
        if size:
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
        result = Cart.add_to_cart(user_id, product_id, quantity, size, color_id)
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

@cart_bp.route('/cart/update/<int:product_id>', methods=['POST'])
@login_required
def update_cart(product_id):
    try:
        # Get form data
        quantity = request.form.get('quantity', type=int)
        color_id = request.form.get('color_id', type=int)
        size = request.form.get('size')
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        
        # Build query to find cart items
        # Ensure we get the correct user ID whether current_user is an object or dict
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        query = CartItem.query.filter_by(user_id=user_id, product_id=product_id, deleted_at=None)
                
        if color_id:
            try:
                query = query.filter_by(color_id=color_id)
            except ValueError:
                if is_ajax:
                    return jsonify({'error': 'Invalid color format'}), 400
                flash('Invalid color format', 'error')
                return redirect(url_for('cart.view_cart'))

        cart_items = query.all()
        if not cart_items:
            if is_ajax:
                return jsonify({'error': 'Item not found in cart'}), 404
            flash('Item not found in cart', 'error')
            return redirect(url_for('cart.view_cart'))

        # Update quantity
        try:
            quantity = int(request.form.get('quantity', 0))
            if quantity < 0:
                raise ValueError('Quantity must be non-negative')
        except ValueError as e:
            if is_ajax:
                return jsonify({'error': str(e)}), 400
            flash(str(e), 'error')
            return redirect(url_for('cart.view_cart'))

        # Update cart item
        cart_item = cart_items[0]

        # Handle removing item if quantity is 0
        if quantity == 0:
            cart_item.deleted_at = datetime.utcnow()  # Soft delete
            db.session.commit()
            if is_ajax:
                return jsonify({'success': True, 'message': 'Item removed from cart'})
            flash('Item removed from cart', 'success')
            return redirect(url_for('cart.view_cart'))
        
        # Update quantity
        cart_item.quantity = quantity
        db.session.commit()
        
        if is_ajax:
            return jsonify({'success': True, 'message': 'Cart updated'})
        
        flash('Cart updated successfully', 'success')
        return redirect(url_for('cart.view_cart'))

    except Exception as e:
        current_app.logger.error(f"Error updating cart: {str(e)}")
        if is_ajax:
            return jsonify({'error': 'Failed to update cart'}), 500
        flash('An error occurred while updating your cart.', 'error')
        return redirect(url_for('cart.view_cart'))

@cart_bp.route('/cart/remove/<int:product_id>', methods=['POST'])
@login_required
def remove_from_cart(product_id):
    try:
        # Get form data
        size = request.form.get('size')
        color_id = request.form.get('color_id')
        
        # Ensure we get the correct user ID whether current_user is an object or dict
        user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
        
        if Cart.remove_from_cart(user_id, product_id, size=size, color_id=color_id):
            flash('Item removed from cart', 'success')
        else:
            flash('Item not found in cart', 'error')
    except Exception as e:
        current_app.logger.error(f"Error removing from cart: {str(e)}")
        current_app.logger.error("Stack trace:", exc_info=True)
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
                # Ensure we get the correct user ID whether current_user is an object or dict
                user_id = current_user['id'] if isinstance(current_user, dict) else current_user.id
                cart = Cart.get_cart_for_user(user_id)
                if not cart or not cart['items']:
                    return jsonify({'success': False, 'error': 'Your cart is empty'}), 400
                
                # Prepare shipping address
                shipping_address = f"{shipping_info.get('address', '')}"
                if shipping_info.get('address2'):
                    shipping_address += f", {shipping_info.get('address2')}"
                shipping_address += f", {shipping_info.get('city', '')}, {shipping_info.get('state', '')}, {shipping_info.get('zip', '')}"
                
                # Create order
                order = Order(
                    user_id=user_id,  # Using already extracted user_id
                    status=OrderStatus.PENDING_PAYMENT if payment_method == 'payos' else OrderStatus.PROCESSING,
                    total_amount=cart['total'],
                    shipping_address=shipping_address,
                    billing_address=shipping_address,  # Using same address for billing
                    billing_first_name=shipping_info.get('first_name'),
                    billing_last_name=shipping_info.get('last_name'),
                    payment_method=payment_method
                )
                db.session.add(order)
                db.session.flush()  # Get order ID without committing yet
                
                # Add order items
                for item in cart['items']:
                    product = Product.query.get(item['product_id'])
                    if product:
                        # Add item to order
                        order.add_item(
                            product_id=product.id,
                            quantity=item['quantity'],
                            price=item['price'],
                            size=item.get('size')
                        )
                
                # Handle payment method
                if payment_method == 'payos':
                    # Process PayOS payment
                    from payment_providers import PayOSAPI
                    payos = PayOSAPI()
                    
                    # Create payment request
                    payment_result = payos.create_payment(
                        order_id=str(order.id),
                        amount=order.total_amount,
                        description=f"Payment for order {order.id}"
                    )
                    
                    if payment_result['success']:
                        # Save the payment URL and commit the order
                        db.session.commit()
                        
                        # Return payment URL to redirect user
                        return jsonify({
                            'success': True,
                            'requires_payment': True,
                            'payment_url': payment_result['payment_url'],
                            'order_id': order.id
                        })
                    else:
                        # Payment creation failed
                        db.session.rollback()
                        return jsonify({
                            'success': False,
                            'error': payment_result.get('error', 'Failed to create payment')
                        }), 400
                else:
                    # COD order, just commit and return success
                    db.session.commit()
                    
                    # Clear the cart
                    Cart.clear_cart(user_id)  # Using already extracted user_id
                    
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
                       shipping_cost=cart_data['shipping_cost'],
                       total=cart_data['total'],
                       cart_item_count=len(cart_data['items']))