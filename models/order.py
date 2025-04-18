from extensions import db
from datetime import datetime, timezone, timedelta
from enum import Enum

def to_vietnam_time(utc_dt):
    """Convert UTC datetime to Vietnam time (UTC+7)"""
    if utc_dt is None:
        return None
    vietnam_tz = timezone(timedelta(hours=7))
    return utc_dt.replace(tzinfo=timezone.utc).astimezone(vietnam_tz)

class OrderStatus(Enum):
    PENDING_PAYMENT = 'PENDING_PAYMENT'  # Initial state when order is created
    PAID = 'PAID'                # Payment confirmed
    PROCESSING = 'PROCESSING'    # Order being processed
    SHIPPED = 'SHIPPED'         # Order has been shipped
    DELIVERED = 'DELIVERED'     # Order delivered to customer
    CANCELLED = 'CANCELLED'     # Order cancelled/payment failed
    REFUNDED = 'REFUNDED'      # Payment was refunded

    @classmethod
    def from_string(cls, value):
        """Convert string to enum member, case-insensitive"""
        try:
            return cls._value2member_map_[value.upper()]
        except KeyError:
            if value.upper() == 'CANCELLED':
                return cls.CANCELLED
            raise ValueError(f"'{value}' is not a valid {cls.__name__}")

    def __str__(self):
        return str(self.value)
    
    @classmethod
    def _missing_(cls, value):
        """Handle case-insensitive lookup for enum values"""
        if isinstance(value, str):
            upper_value = value.upper()
            for member in cls:
                if member.value == upper_value:
                    return member
            if (upper_value == 'CANCELLED'):
                return cls.CANCELLED

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING_PAYMENT)
    cancellation_requested = db.Column(db.Boolean, default=False)
    cancellation_reason = db.Column(db.Text)
    cancellation_approved = db.Column(db.Boolean, nullable=True)  # None = chưa duyệt
    total_amount = db.Column(db.Integer, nullable=False)  # Amount in VND
    shipping_fee = db.Column(db.Integer, nullable=False, default=115000)  # Default shipping fee in VND
    # Remove or comment out this line since it's duplicated below
    # shipping_address = db.Column(db.Text, nullable=False)
    # Billing information
    billing_first_name = db.Column(db.String(100))
    billing_last_name = db.Column(db.String(100))
    billing_address = db.Column(db.Text)
    billing_city = db.Column(db.String(100))
    billing_state = db.Column(db.String(100))
    billing_zip = db.Column(db.String(20))
    payment_method = db.Column(db.String(50), nullable=False)
    payment_id = db.Column(db.String(100))  # External payment reference
    tracking_number = db.Column(db.String(100))
    checkout_url = db.Column(db.String(500))  # PayOS checkout URL
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Add shipping information fields
    shipping_first_name = db.Column(db.String(100))
    shipping_last_name = db.Column(db.String(100))
    shipping_address = db.Column(db.String(200))  # This one should be kept
    shipping_address2 = db.Column(db.String(200), nullable=True)
    shipping_city = db.Column(db.String(100))
    shipping_state = db.Column(db.String(100))
    shipping_zip = db.Column(db.String(20))
    shipping_phone = db.Column(db.String(20))
    
    # Relationships
    items = db.relationship('OrderItem', back_populates='order', lazy=True, cascade='all, delete-orphan')
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)
    
    @property
    def subtotal(self):
        """Calculate order subtotal (before shipping)"""
        return sum(item.quantity * item.price for item in self.items)
    
    @property
    def shipping_cost(self):
        """Get shipping cost with fallback to default if column doesn't exist yet"""
        try:
            return self.shipping_fee
        except AttributeError:
            return 115000  # Default shipping fee
    
    @property
    def total(self):
        """Calculate total amount (subtotal + shipping)"""
        return self.subtotal + self.shipping_cost

    def add_item(self, product_id, quantity, price, size=None):
        """Add an item to the order"""
        item = OrderItem(
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            price=price,
            size=size
        )
        db.session.add(item)
        return item
    
    def update_status(self, new_status):
        """Update order status with validation"""
        if isinstance(new_status, str):
            new_status = OrderStatus.from_string(new_status)
        if not isinstance(new_status, OrderStatus):
            raise ValueError("Invalid status")
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def to_dict(self):
        vietnam_created = to_vietnam_time(self.created_at)
        vietnam_updated = to_vietnam_time(self.updated_at)
        
        # Safely get shipping_fee with fallback
        try:
            shipping_fee = self.shipping_fee
        except (AttributeError, Exception):
            shipping_fee = 115000  # Default to 115000 VND if not set
        
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status.value,
            'total_amount': self.total_amount,
            'shipping_fee': shipping_fee,
            'shipping_address': self.shipping_address,
            'billing_first_name': self.billing_first_name,
            'billing_last_name': self.billing_last_name,
            'billing_address': self.billing_address,
            'billing_city': self.billing_city,
            'billing_state': self.billing_state,
            'billing_zip': self.billing_zip,
            'payment_method': self.payment_method,
            'has_saved_payment': bool(self.payment_id),
            'payment_status': 'Processed' if self.payment_id else 'Pending',
            'cancellation_requested': self.cancellation_requested,
            'cancellation_reason': self.cancellation_reason,
            'cancellation_approved': self.cancellation_approved,
            'tracking_number': self.tracking_number,
            'checkout_url': self.checkout_url,
            'notes': self.notes,
            'item_count': self.item_count,
            'items': [item.to_dict() for item in self.items],
            'created_at': vietnam_created.isoformat(),
            'updated_at': vietnam_updated.isoformat(),
            'created_at_local': vietnam_created.strftime('%B %d, %Y at %I:%M %p'),
            'updated_at_local': vietnam_updated.strftime('%B %d, %Y at %I:%M %p')
        }
    
    def __repr__(self):
        return f'<Order {self.id}>'

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    size = db.Column(db.String(20), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    
    # Relationships
    order = db.relationship('Order', back_populates='items', lazy=True)
    product = db.relationship('Product', lazy=True)
    color = db.relationship('ProductColor', lazy=True)
    variant = db.relationship('ProductVariant', lazy=True)
    
    @property
    def subtotal(self):
        """Calculate subtotal in VND"""
        return self.quantity * self.price
    
    def to_dict(self):
        vietnam_created = to_vietnam_time(self.created_at)
        return {
            'id': self.id,
            'product': self.product.to_dict(),
            'size': self.size,
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.subtotal,
            'created_at': vietnam_created.isoformat(),
            'created_at_local': vietnam_created.strftime('%B %d, %Y at %I:%M %p')
        }
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'