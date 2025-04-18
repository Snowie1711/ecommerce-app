from flask_login import UserMixin
from extensions import db
from sqlalchemy import event
from datetime import datetime
from sqlalchemy.orm import relationship
from werkzeug.security import generate_password_hash, check_password_hash

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    # Basic Information
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=True)  # Made nullable for OAuth users
    password_hash = db.Column(db.String(200), nullable=True)  # Made nullable for OAuth users
    profile_picture = db.Column(db.String(500))  # URL to user's profile picture
    first_name = db.Column(db.String(50))
    last_name = db.Column(db.String(50))

    # Address Information
    address_line1 = db.Column(db.String(100))
    address_line2 = db.Column(db.String(100))
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(10))
    phone_number = db.Column(db.String(20))

    # OAuth Information
    provider = db.Column(db.String(50))  # OAuth provider (e.g., 'google')
    oauth_token = db.Column(db.JSON)     # OAuth token data

    # Payment Information
    payment_method_id = db.Column(db.String(100))  # Reference to securely stored payment method
    payment_provider = db.Column(db.String(50))    # e.g., 'credit_card', 'payos', 'cod'

    # Administrative
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart_items = relationship("CartItem",
                          backref=db.backref("user", lazy=True),
                          lazy=True,
                          primaryjoin="and_(User.id==CartItem.user_id, CartItem.deleted_at.is_(None))")
    orders = relationship("Order", backref="user", lazy=True)

    # Password handling
    _password = None
    
    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

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

    def __repr__(self):
        return f'<User {self.email}>'

# Update timestamps on save
@event.listens_for(User, 'before_insert')
def set_user_timestamps(mapper, connection, target):
    now = datetime.utcnow()
    target.created_at = now
    target.updated_at = now

@event.listens_for(User, 'before_update')
def update_user_timestamp(mapper, connection, target):
    target.updated_at = datetime.utcnow()