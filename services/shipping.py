"""
Shipping service for the e-commerce application
"""
from flask import current_app

def calculate_shipping_cost(cart_items=None, subtotal=0, address=None):
    """
    Calculate shipping cost for an order. This implementation provides free shipping.
    
    Args:
        cart_items: List of cart items (optional)
        subtotal: Order subtotal (optional)
        address: Shipping address information (optional)
        
    Returns:
        int: Always returns 0 (free shipping)
    """
    # Log that free shipping is being applied
    current_app.logger.info("Applying free shipping policy")
    
    # Always return 0 (free shipping)
    return 0

def get_shipping_methods():
    """
    Get available shipping methods.
    
    Returns:
        list: List of shipping method dictionaries
    """
    return [
        {
            'id': 'free',
            'name': 'Miễn phí vận chuyển',
            'description': 'Miễn phí vận chuyển cho tất cả đơn hàng',
            'price': 0,
        }
    ]

def get_shipping_display_text():
    """
    Get the display text for shipping.
    
    Returns:
        str: "Miễn phí vận chuyển" (Free shipping)
    """
    return "Miễn phí vận chuyển"
