from flask import Blueprint, request, redirect, url_for, flash, session
from flask_login import login_required, current_user
from app import db
# Fix import paths according to your project structure
from models.order import Order, OrderStatus
from models.cart import Cart

bp = Blueprint('cart', __name__)

# ...existing code...

@bp.route('/checkout', methods=['POST'])
@login_required
def checkout():
    # Get cart data to calculate total
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Your cart is empty', 'error')
        return redirect(url_for('cart.view'))
        
    # Calculate total and shipping fee
    subtotal = sum(item.quantity * item.product.price for item in cart.items)
    shipping_fee = 115000  # Default shipping fee
    total = subtotal + shipping_fee
    
    # Extract payment_method from form data
    payment_method = request.form.get('payment_method')
    
    # If payment method is PayOS, delete pending payment orders
    if payment_method == 'payos':
        # Find all pending payment orders for current user
        pending_orders = Order.query.filter_by(
            user_id=current_user.id, 
            status=OrderStatus.PENDING_PAYMENT
        ).all()
        
        # Delete each pending order
        for order in pending_orders:
            db.session.delete(order)
        
        # Commit the deletions before creating a new order
        db.session.commit()
    
    # Continue with order creation as before
    order = Order(
        user_id=current_user.id,
        status=OrderStatus.PENDING_PAYMENT,
        total_amount=total,
        shipping_fee=shipping_fee,
        # ...existing order fields...
    )
    
    # ...existing code for adding items to order...
    
    # ...existing code for handling payment processing...
    
    # ...existing code for redirecting user...