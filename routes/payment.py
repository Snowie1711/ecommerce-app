from flask import Blueprint, render_template, request, jsonify, current_app
from flask_wtf.csrf import CSRFProtect
from models.order import Order, OrderStatus
from models import db
from models.cart import Cart
import json
from payment_providers.payos import PayOSAPI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

payment = Blueprint('payment', __name__)
csrf = CSRFProtect()

def get_payos_api():
    """Get or create PayOSAPI instance"""
    if not hasattr(get_payos_api, '_api'):
        get_payos_api._api = PayOSAPI()
    return get_payos_api._api

@payment.route('/create-payment', methods=['POST'])
def create_payment():
    try:
        # Log request details
        current_app.logger.info(f"""
        Payment Request:
        Headers: {dict(request.headers)}
        Form: {dict(request.form)}
        JSON: {request.get_json(silent=True)}
        """)

        # Validate request
        if not request.is_json:
            return jsonify({"success": False, "error": "Invalid request format"}), 400

        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No payment data provided"}), 400

        # Required fields validation
        required_fields = ['order_id', 'amount']
        for field in required_fields:
            if field not in data:
                return jsonify({"success": False, "error": f"Missing required field: {field}"}), 400

        try:
            # Ensure amount is a valid integer in VND
            amount_vnd = data['amount']
            if isinstance(amount_vnd, str):
                # Remove " VND" suffix and commas if present
                amount_vnd = amount_vnd.replace(' VND', '').replace(',', '')
            
            amount_vnd = int(float(amount_vnd))
            order_id = int(data['order_id'])

            # Create PayOS payment
            api = get_payos_api()
            result = api.create_payment(
                str(order_id), 
                amount_vnd,
                f"Payment for order #{order_id}"
            )
            
            if not result.get('success'):
                return jsonify(result), 400
                
            return jsonify(result)

        except (ValueError, TypeError) as e:
            current_app.logger.error(f"Invalid data format: {str(e)}")
            return jsonify({
                "success": False,
                "error": "Invalid data format"
            }), 400

    except Exception as e:
        current_app.logger.error(f"Payment error: {str(e)}")
        return jsonify({
            "success": False,
            "error": "System error",
            "details": str(e)
        }), 500

@payment.route('/webhook', methods=['POST'])
def webhook():
    """Handle PayOS payment webhook"""
    try:
        webhook_data = request.json
        api = get_payos_api()
        
        # Verify webhook signature
        if not api.verify_webhook(webhook_data):
            current_app.logger.error('Payment webhook: Signature verification failed')
            return jsonify({"code": "97", "desc": "Invalid signature"}), 400

        # Get order details from webhook data
        order_id = webhook_data.get('orderCode')
        status = webhook_data.get('status')
        transaction_id = webhook_data.get('transactionId')

        # Get order from database
        try:
            order = Order.query.get(int(order_id))
        except (ValueError, TypeError):
            current_app.logger.error(f'Payment webhook: Invalid order ID format: {order_id}')
            return jsonify({"code": "01", "desc": "Invalid order ID format"}), 400

        if not order:
            current_app.logger.error(f'Payment webhook: Order not found: {order_id}')
            return jsonify({"code": "01", "desc": "Order not found"}), 400

        # Update order status based on payment status
        if status == 'PAID':  # Payment successful
            order.status = OrderStatus.PAID
            order.payment_id = transaction_id
            
            # Update product stock levels
            for item in order.items:
                item.product.stock -= item.quantity
                if item.product.stock < 0:
                    current_app.logger.warning(f'Negative stock for product {item.product.id} after order {order_id}')
            
            # Clear user's cart after successful payment
            Cart.clear_cart(order.user_id)
            
            current_app.logger.info(f'Payment successful for order {order_id}, stock updated')
        elif status == 'CANCELLED':  # Payment cancelled/failed
            order.status = OrderStatus.CANCELLED
            current_app.logger.warning(f'Payment failed for order {order_id}: {webhook_data.get("description")}')
        else:  # Other statuses (PENDING, etc)
            current_app.logger.info(f'Payment status update for order {order_id}: {status}')

        db.session.commit()
        return jsonify({"code": "00", "desc": "success"})

    except Exception as e:
        current_app.logger.exception('Payment webhook error')
        return jsonify({"code": "99", "desc": str(e)}), 500

@payment.route('/payment-result')
def payment_result():
    """Handle payment result redirect"""
    current_app.logger.info("Payment result route accessed")
    
    # Get status and order info
    status = 'success' if request.args.get('status') == 'PAID' else 'failed'
    order_id = request.args.get('orderCode', '')
    
    # Get error info if present
    error = request.args.get('error', '')
    error_message = request.args.get('message', '')
    
    if error:
        current_app.logger.error(f"Payment error: {error} - {error_message}")

    return render_template('payment/result.html',
                         status=status,
                         transaction_id=order_id,
                         error=error,
                         error_message=error_message)