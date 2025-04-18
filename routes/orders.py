from flask import Blueprint, render_template, redirect, url_for, flash, request, abort, current_app, jsonify
from flask_login import login_required, current_user
from models.order import Order, OrderStatus
from models.notification import Notification
from models.review import Review
from extensions import db
from sqlalchemy import desc
import sqlalchemy.exc

orders_bp = Blueprint('orders', __name__, url_prefix='/orders')

@orders_bp.route('/history')
@login_required
def order_history():
    """Display order history for the current user."""
    current_app.logger.info(f"Fetching order history for user {current_user.id}")
    
    try:
        # Get orders for the current user, most recent first
        query = Order.query.filter_by(user_id=current_user.id)\
            .order_by(desc(Order.created_at))
        
        try:
            user_orders = query.all()
        except sqlalchemy.exc.OperationalError as e:
            if 'no such column: orders.shipping_fee' in str(e):
                # If shipping_fee column doesn't exist, run the migration
                current_app.logger.warning("shipping_fee column doesn't exist, attempting to handle")
                
                # We can't run migrations here, but we can inform the user
                flash("Database needs to be updated. Please contact an administrator.", "warning")
                user_orders = []
            else:
                # Re-raise if it's a different error
                raise
        
        return render_template('orders/history.html', orders=user_orders)
    except Exception as e:
        current_app.logger.error(f"Error fetching order history: {str(e)}")
        flash("There was an issue loading your order history. Our team has been notified.", "error")
        return redirect(url_for('main.home'))

@orders_bp.route('/<int:order_id>/request-cancel', methods=['POST'])
@login_required
def request_cancel(order_id):
    """Handle order cancellation request."""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Check if order belongs to current user
        if order.user_id != current_user.id:
            return jsonify({'error': 'Không có quyền hủy đơn hàng này'}), 403
        
        # Check if order is already cancelled
        if order.status == OrderStatus.CANCELLED:
            return jsonify({'error': 'Đơn hàng đã bị hủy'}), 400
            
        # Check if order is already delivered
        if order.status in [OrderStatus.SHIPPED, OrderStatus.DELIVERED]:
            return jsonify({'error': 'Không thể hủy đơn hàng đã giao'}), 400
            
        # Check if cancellation was already requested
        if order.cancellation_requested:
            return jsonify({'error': 'Yêu cầu hủy đã được gửi và đang chờ xử lý'}), 400
        
        # Get reason from request, use default if not provided
        data = request.get_json()
        reason = data.get('reason', 'Người dùng yêu cầu hủy đơn') if data else 'Người dùng yêu cầu hủy đơn'
            
        # Update order
        order.cancellation_requested = True
        order.cancellation_reason = reason
        
        # Create notification for admin
        admin_notification = Notification(
            user_id=1,  # Assuming admin has ID 1
            message=f"New cancellation request for Order #{order.id}",
            link=url_for('admin.order_detail', id=order.id)  # Fixed parameter name to 'id'
        )
        db.session.add(admin_notification)
        
        try:
            db.session.commit()
        except Exception as e:
            current_app.logger.error(f"Error committing transaction: {str(e)}")
            db.session.rollback()
            raise
        
        return jsonify({
            'message': 'Yêu cầu hủy đơn đã được gửi thành công',
            'status': 'pending'
        })
        
    except Exception as e:
        current_app.logger.error(f"Error in request_cancel: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Đã xảy ra lỗi, vui lòng thử lại'}), 500

@orders_bp.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    """Display the details of a specific order."""
    try:
        order = Order.query.get_or_404(order_id)
        
        # Ensure user is allowed to view this order
        if order.user_id != current_user.id and not current_user.is_admin:
            abort(403)

        # Get list of product IDs that the user has reviewed for this order
        reviewed_products = Review.query.filter_by(
            user_id=current_user.id,
            order_id=order_id
        ).with_entities(Review.product_id).all()
        reviewed_product_ids = [r[0] for r in reviewed_products]
        return render_template(
            'orders/detail.html',
            order=order,
            reviewed_product_ids=reviewed_product_ids
        )
    except Exception as e:
        current_app.logger.error(f"Error viewing order details: {str(e)}")
        flash("There was an issue loading the order details. Our team has been notified.", "error")
        return redirect(url_for('orders.order_history'))

def create_order_notification(order, status_change=False):
    """Create a notification for an order event."""
    try:
        message = ""
        if status_change:
            message = f"Order #{order.id} has been updated to {order.status.value}"
        else:
            message = f"Order #{order.id} has been created successfully"
            
        notification = Notification(
            user_id=order.user_id,
            message=message,
            link=url_for('orders.order_detail', order_id=order.id)
        )
        db.session.add(notification)
        db.session.commit()
        
    except Exception as e:
        current_app.logger.error(f"Error creating order notification: {str(e)}")
        # Don't raise the exception since notifications are non-critical
        pass
