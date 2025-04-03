from . import db
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
            if upper_value == 'CANCELLED':
                return cls.CANCELLED

class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), nullable=False, default=OrderStatus.PENDING_PAYMENT)
    total_amount = db.Column(db.Integer, nullable=False)  # Amount in VND
    shipping_address = db.Column(db.Text, nullable=False)
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
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('OrderItem', back_populates='order', lazy=True, cascade='all, delete-orphan')
    
    @property
    def item_count(self):
        return sum(item.quantity for item in self.items)
    
    def add_item(self, product_id, quantity, price):
        """Add an item to the order"""
        item = OrderItem(
            order_id=self.id,
            product_id=product_id,
            quantity=quantity,
            price=price
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
        return {
            'id': self.id,
            'user_id': self.user_id,
            'status': self.status.value,
            'total_amount': self.total_amount,
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
            'tracking_number': self.tracking_number,
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
    quantity = db.Column(db.Integer, nullable=False)
    price = db.Column(db.Integer, nullable=False)  # Price in VND at time of purchase
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    order = db.relationship('Order', back_populates='items', lazy=True)
    product = db.relationship('Product', back_populates='order_items', lazy=True)
    
    @property
    def subtotal(self):
        """Calculate subtotal in VND"""
        return self.quantity * self.price
    
    def to_dict(self):
        vietnam_created = to_vietnam_time(self.created_at)
        return {
            'id': self.id,
            'product': self.product.to_dict(),
            'quantity': self.quantity,
            'price': self.price,
            'subtotal': self.subtotal,
            'created_at': vietnam_created.isoformat(),
            'created_at_local': vietnam_created.strftime('%B %d, %Y at %I:%M %p')
        }
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'