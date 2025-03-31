from flask_login import UserMixin
from models import db
from sqlalchemy import event
from datetime import datetime
from sqlalchemy.orm import relationship

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(10))
    phone_number = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Payment information
    payment_method_id = db.Column(db.String(100))  # Reference to securely stored payment method
    payment_provider = db.Column(db.String(50))    # e.g., 'credit_card', 'payos', 'cod'
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationships
    cart_items = relationship("CartItem",
                            backref=db.backref("user", lazy=True),
                            lazy=True,
                            primaryjoin="and_(User.id==CartItem.user_id, CartItem.deleted_at.is_(None))")
    orders = relationship("Order", backref="user", lazy=True)

    def __repr__(self):
        return f'<User {self.email}>'
    
    def to_dict(self):
        """Convert user object to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'is_admin': self.is_admin
        }

# Update timestamps on save
@event.listens_for(User, 'before_insert')
def set_user_timestamps(mapper, connection, target):
    now = datetime.utcnow()
    target.created_at = now
    target.updated_at = now

@event.listens_for(User, 'before_update')
def update_user_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()