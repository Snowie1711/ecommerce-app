from . import db
from datetime import datetime
from sqlalchemy import text
from flask import current_app
from models.product import Product  # Add explicit import

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Define relationship with Product
    product = db.relationship('Product',
                          back_populates='cart_items',
                          lazy='joined',
                          foreign_keys=[product_id])
    
    @property
    def is_active(self):
        """Check if cart item is active (not soft deleted)"""
        return self.deleted_at is None
    
    @property
    def subtotal(self):
        """Calculate subtotal in VND"""
        return self.quantity * self.product.price if self.product else 0
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict() if self.product else None,
            'quantity': self.quantity,
            'subtotal': self.subtotal,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Cart:
    """Cart utility class for managing cart operations"""
    
    @staticmethod
    def get_user_cart(user_id):
        """Get all active cart items for a user"""
        try:
            current_app.logger.info(f"=== Retrieving Cart for User {user_id} ===")
            
            # Get basic cart items first (no joins)
            cart_items = (CartItem.query
                         .filter(
                             CartItem.user_id == user_id,
                             CartItem.deleted_at.is_(None)
                         )
                         .all())
            
            current_app.logger.info(f"Found {len(cart_items)} items in cart")
            
            if not cart_items:
                current_app.logger.info(f"No items in cart for user {user_id}")
                return []
            
            # Start transaction for any updates needed
            db.session.begin(nested=True)
            try:
                valid_items = []
                invalid_items = []
                
                for item in cart_items:
                    # Verify product exists and load it
                    product = (Product.query
                             .filter_by(id=item.product_id)
                             .first())
                    
                    if product:
                        current_app.logger.info(
                            f"Found cart item - Product: {product.name}, "
                            f"Quantity: {item.quantity}, "
                            f"Stock: {product.stock}"
                        )
                        # Keep item but log warning if out of stock
                        if product.stock <= 0:
                            current_app.logger.warning(
                                f"Product {product.name} is out of stock"
                            )
                        elif item.quantity > product.stock:
                            current_app.logger.warning(
                                f"Quantity {item.quantity} exceeds stock {product.stock}"
                            )
                        valid_items.append(item)
                    else:
                        current_app.logger.warning(
                            f"Cart item {item.id} references missing product {item.product_id}"
                        )
                        invalid_items.append(item)
                
                # Clean up invalid items
                for item in invalid_items:
                    item.deleted_at = datetime.utcnow()
                    db.session.add(item)
                
                # Commit any changes
                if invalid_items:
                    db.session.commit()
                    current_app.logger.info(f"Removed {len(invalid_items)} invalid items")
                
                current_app.logger.info(f"Returning {len(valid_items)} valid cart items")
                return valid_items
                
            except Exception as e:
                current_app.logger.error(f"Error processing cart items: {str(e)}")
                db.session.rollback()
                raise
                
        except Exception as e:
            current_app.logger.error(f"Error retrieving cart: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return []
    
    @staticmethod
    def get_cart_total(user_id):
        """Calculate total price and shipping cost of all items in cart"""
        try:
            cart_items = Cart.get_user_cart(user_id)
            
            if not cart_items:
                return {
                    'subtotal': 0.0,
                    'shipping_cost': 0.0,
                    'total': 0.0
                }
            
            # Calculate subtotal
            subtotal = sum(item.subtotal for item in cart_items if item.product)
            
            # Calculate shipping cost (free if subtotal >= 1M VND)
            shipping_cost = 0 if subtotal >= 1000000 else 50000
            
            # Calculate total
            total = subtotal + shipping_cost
            
            current_app.logger.info(f"""
            Cart Total Calculation:
            - Subtotal: {subtotal:,} VND
            - Shipping: {shipping_cost:,} VND
            - Total: {total:,} VND
            """)
            
            return {
                'subtotal': float(subtotal),
                'shipping_cost': float(shipping_cost),
                'total': float(total)
            }
            
        except Exception as e:
            current_app.logger.error(f"Error calculating cart total: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return {
                'subtotal': 0.0,
                'shipping_cost': 0.0,
                'total': 0.0
            }
    
    @staticmethod
    def add_to_cart(user_id, product_id, quantity=1):
        """Add a product to cart or update quantity if already exists"""
        try:
            # Start transaction
            db.session.begin(nested=True)
            
            try:
                # Verify product exists
                product = Product.query.get(product_id)
                if not product:
                    current_app.logger.error(f"Product {product_id} not found")
                    db.session.rollback()
                    return None
                
                # Get or create cart item
                cart_item = (CartItem.query
                           .filter_by(
                               user_id=user_id,
                               product_id=product_id,
                               deleted_at=None
                           )
                           .first())
                
                if cart_item:
                    # Update existing item
                    cart_item.quantity += quantity
                    cart_item.updated_at = datetime.utcnow()
                    current_app.logger.info(
                        f"Updated quantity for item {cart_item.id} "
                        f"to {cart_item.quantity}"
                    )
                else:
                    # Create new item
                    cart_item = CartItem(
                        user_id=user_id,
                        product_id=product_id,
                        quantity=quantity
                    )
                    db.session.add(cart_item)
                    current_app.logger.info(
                        f"Created new cart item with quantity {quantity}"
                    )
                
                # Commit changes
                db.session.commit()
                current_app.logger.info("Successfully saved cart changes")
                return cart_item
                
            except Exception as e:
                current_app.logger.error(f"Error processing cart changes: {str(e)}")
                db.session.rollback()
                raise
                
        except Exception as e:
            current_app.logger.error(f"Error adding to cart: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return None
    
    @staticmethod
    def update_quantity(user_id, product_id, quantity):
        """Update quantity of a cart item"""
        try:
            # Start transaction
            db.session.begin(nested=True)
            
            try:
                # Find cart item
                cart_item = (CartItem.query
                           .filter_by(
                               user_id=user_id,
                               product_id=product_id,
                               deleted_at=None
                           )
                           .first())
                
                if not cart_item:
                    current_app.logger.warning(f"No active cart item found")
                    db.session.rollback()
                    return None
                
                if quantity > 0:
                    cart_item.quantity = quantity
                    cart_item.updated_at = datetime.utcnow()
                    
                    # Commit changes
                    db.session.commit()
                    current_app.logger.info(f"Updated quantity to {quantity}")
                    return cart_item
                else:
                    return Cart.remove_from_cart(user_id, product_id)
                
            except Exception as e:
                current_app.logger.error(f"Error processing quantity update: {str(e)}")
                db.session.rollback()
                raise
                
        except Exception as e:
            current_app.logger.error(f"Error updating cart quantity: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return None
    
    @staticmethod
    def remove_from_cart(user_id, product_id):
        """Soft delete a product from cart"""
        try:
            # Start transaction
            db.session.begin(nested=True)
            
            try:
                # Find cart item
                cart_item = (CartItem.query
                           .filter_by(
                               user_id=user_id,
                               product_id=product_id,
                               deleted_at=None
                           )
                           .first())
                
                if not cart_item:
                    current_app.logger.warning(f"No active cart item found")
                    db.session.rollback()
                    return False
                
                # Soft delete
                cart_item.deleted_at = datetime.utcnow()
                
                # Commit changes
                db.session.commit()
                current_app.logger.info(f"Removed cart item {cart_item.id}")
                return True
                
            except Exception as e:
                current_app.logger.error(f"Error processing cart item removal: {str(e)}")
                db.session.rollback()
                raise
                
        except Exception as e:
            current_app.logger.error(f"Error removing from cart: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return False
    
    @staticmethod
    def clear_cart(user_id):
        """Soft delete all items from cart"""
        try:
            # Start transaction
            db.session.begin(nested=True)
            
            try:
                # Get all active items
                cart_items = (CartItem.query
                           .filter_by(
                               user_id=user_id,
                               deleted_at=None
                           )
                           .all())
                
                if not cart_items:
                    current_app.logger.info(f"No active items to clear")
                    db.session.commit()
                    return True
                
                # Soft delete all items
                now = datetime.utcnow()
                for item in cart_items:
                    item.deleted_at = now
                
                # Commit changes
                db.session.commit()
                current_app.logger.info(f"Cleared {len(cart_items)} items")
                return True
                
            except Exception as e:
                current_app.logger.error(f"Error processing cart clear: {str(e)}")
                db.session.rollback()
                raise
                
        except Exception as e:
            current_app.logger.error(f"Error clearing cart: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return False