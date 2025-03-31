from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime

# Initialize SQLAlchemy instance
db = SQLAlchemy()

# Import models after db initialization to avoid circular imports
# First import models with no dependencies
from .category import Category
from .product_image import ProductImage

# Then import models that depend on the above
from .product import Product

# Then import models that depend on Product
from .cart import CartItem, Cart
from .order import Order, OrderItem, OrderStatus

# Finally import User which depends on Cart and Order
from .user import User

__all__ = ['db', 'User', 'Product', 'Category', 'CartItem', 'Cart', 'Order', 'OrderItem', 'OrderStatus', 'ProductImage']