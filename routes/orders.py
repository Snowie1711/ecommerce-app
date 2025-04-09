from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app
from flask_login import login_required, current_user
from models.order import Order, OrderStatus
from models import db

orders_bp = Blueprint('orders', __name__)

@orders_bp.route('/')
@login_required
def list_orders():
    """Display a list of the user's orders."""
    current_app.logger.info(f"Fetching orders for user {current_user.id}")
    
    # Get orders for the current user, most recent first
    user_orders = Order.query.filter_by(user_id=current_user.id).order_by(Order.created_at.desc()).all()
    
    return render_template('orders/list.html', orders=user_orders)

@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    """Display the details of a specific order."""
    order = Order.query.get_or_404(order_id)
    
    # Ensure the order belongs to the current user
    if order.user_id != current_user.id:
        current_app.logger.warning(f"User {current_user.id} attempted to access order {order_id} belonging to user {order.user_id}")
        abort(403)  # Forbidden
    
    return render_template('orders/detail.html', order=order)
