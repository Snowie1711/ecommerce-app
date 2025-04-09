from flask import Blueprint, render_template, request, jsonify, current_app, redirect, url_for, flash
from flask_login import current_user, login_required
from flask_wtf.csrf import CSRFProtect
from models.order import Order, OrderStatus
from models.cart import Cart
from models import db
import json
from payment_providers.payos import PayOSAPI
from datetime import datetime
from dotenv import load_dotenv
from error_handlers import handle_errors

# Load environment variables
load_dotenv()

payment_bp = Blueprint('payment', __name__, url_prefix='/payment')
csrf = CSRFProtect()

def get_payos_api():
    """Get or create PayOSAPI instance"""
    if not hasattr(get_payos_api, '_api'):
        get_payos_api._api = PayOSAPI()
    return get_payos_api._api

@payment_bp.route('/process', methods=['POST'])
@login_required
@handle_errors
def process_payment():
    """Process payment for an order"""
    try:
        data = request.json or {}
        order_id = data.get('order_id')
        payment_method = data.get('payment_method', 'payos')
        
        # Validate order ID
        if not order_id:
            return jsonify({'success': False, 'error': 'Missing order ID'}), 400
        
        # Get order from database
        order = Order.query.filter_by(id=order_id, user_id=current_user.id).first()
        if not order:
            return jsonify({'success': False, 'error': 'Order not found'}), 404
        
        # Handle different payment methods
        if payment_method == 'payos':
            # Create PayOS payment
            api = get_payos_api()
            amount = order.total_amount
            description = f"Payment for order {order.id}"
            
            current_app.logger.info(f"Creating PayOS payment for order {order_id} with amount {amount} VND")
            result = api.create_payment(str(order_id), amount, description)
            
            if not result.get('success'):
                current_app.logger.error(f"PayOS payment creation failed: {result.get('error')}")
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Payment initialization failed')
                }), 400
            
            # Update order with payment info
            order.payment_method = 'payos'
            db.session.commit()
            
            return jsonify({
                'success': True,
                'redirect_url': result.get('payment_url'),
                'requires_redirect': True
            })
        
        elif payment_method == 'cod':
            # Update order status for Cash on Delivery
            order.payment_method = 'cod'
            order.status = OrderStatus.PROCESSING
            db.session.commit()
            
            # Clear user's cart
            Cart.clear_cart(current_user.id)
            
            return jsonify({
                'success': True,
                'redirect_url': url_for('orders.order_detail', order_id=order.id),
                'requires_redirect': False,
                'message': 'Your order has been placed successfully!'
            })
        
        else:
            return jsonify({
                'success': False,
                'error': 'Invalid payment method'
            }), 400
            
    except Exception as e:
        current_app.logger.error(f"Payment processing error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your payment'
        }), 500

@payment_bp.route('/payment-result')
def payment_result():
    """Handle payment result redirects from PayOS"""
    # Get parameters from the PayOS redirect
    status = request.args.get('status', 'unknown')
    order_id = request.args.get('orderCode')
    error_code = request.args.get('errorCode')
    transaction_id = request.args.get('transactionId', '')
    
    current_app.logger.info(f"Payment result received: status={status}, order_id={order_id}")
    
    # If we have an order ID, find it and update it accordingly
    if order_id:
        try:
            order = Order.query.get(int(order_id))
            
            if order:
                if status == 'success':
                    # Payment was successful
                    order.status = OrderStatus.PAID
                    order.payment_id = transaction_id
                    db.session.commit()
                    
                    # Clear user's cart
                    Cart.clear_cart(order.user_id)
                    
                    if current_user.is_authenticated and current_user.id == order.user_id:
                        flash('Payment successful! Your order has been confirmed.', 'success')
                        return redirect(url_for('orders.order_detail', order_id=order.id))
                else:
                    # Payment failed
                    current_app.logger.warning(f"Payment failed for order {order_id}, status: {status}, error: {error_code}")
                    
                    if status == 'cancel':
                        flash('Payment was cancelled.', 'warning')
                    else:
                        flash('Payment failed. Please try again or choose a different payment method.', 'error')
                    
                    if current_user.is_authenticated and current_user.id == order.user_id:
                        return redirect(url_for('cart.checkout'))
        except Exception as e:
            current_app.logger.error(f"Error processing payment result: {str(e)}")
    
    # Default case or error case
    return render_template('payment/result.html',
                          status=status,
                          transaction_id=transaction_id,
                          error=error_code)

@payment_bp.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayOS webhook notifications"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'success': False, 'message': 'No data received'}), 400
        
        api = get_payos_api()
        if not api.verify_webhook(data):
            current_app.logger.warning('Invalid webhook signature')
            return jsonify({'success': False, 'message': 'Invalid signature'}), 400
        
        order_code = data.get('orderCode')
        status = data.get('status')
        
        if not order_code or not status:
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        order = Order.query.get(int(order_code))
        if not order:
            return jsonify({'success': False, 'message': 'Order not found'}), 404
        
        # Update order status based on webhook data
        if status == 'success':
            order.status = OrderStatus.PAID
            order.payment_id = data.get('transactionId')
            # Clear user's cart
            Cart.clear_cart(order.user_id)
            db.session.commit()
            
        elif status == 'failed' or status == 'cancel':
            order.status = OrderStatus.CANCELLED
            db.session.commit()
            
        current_app.logger.info(f"Webhook processed for order {order_code} with status {status}")
        return jsonify({'success': True, 'message': 'Webhook processed successfully'})
        
    except Exception as e:
        current_app.logger.error(f"Webhook processing error: {str(e)}")
        return jsonify({'success': False, 'message': 'Error processing webhook'}), 500