from . import db
from datetime import datetime
from sqlalchemy import text
from flask import current_app

class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)

    # Define relationship with Product (match the name in Product model)
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
        """Calculate subtotal in base currency (USD)"""
        return self.quantity * self.product.price
    
    def to_dict(self):
        return {
            'id': self.id,
            'product': self.product.to_dict(),
            'quantity': self.quantity,
            'subtotal': self.subtotal,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

class Cart:
    """
    Cart utility class for managing cart operations
    This is not a database model, but a helper class to manage cart items
    """
    
    @staticmethod
    def get_user_cart(user_id):
        """Get all cart items for a user"""
        try:
            # Log cart retrieval attempt
            current_app.logger.info(f"=== Retrieving Cart for User {user_id} ===")
            
            # Direct SQL query for cart validation
            sql = text("""
                SELECT
                    COUNT(*) as count,
                    COALESCE(SUM(ci.quantity * p.price), 0) as total
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = :user_id
            """)
            
            # Execute query with error handling
            try:
                result = db.session.execute(sql, {"user_id": user_id}).first()
                current_app.logger.info(f"""
                Cart SQL Query Result:
                - Count: {result.count if result else 0}
                - Total: {result.total if result else 0}
                """)
            except Exception as e:
                current_app.logger.error(f"Cart SQL error: {str(e)}")
                result = None
            
            current_app.logger.info(f"Direct SQL count: {result} items in cart_items table")
            
            # Get active cart items through SQLAlchemy
            cart_items = CartItem.query.filter_by(
                user_id=user_id,
                deleted_at=None
            ).all()
            
            # Detailed logging
            current_app.logger.info("=== Cart Details ===")
            current_app.logger.info(f"SQLAlchemy query found: {len(cart_items) if cart_items else 0} items")
            
            if cart_items:
                for item in cart_items:
                    # Check if product exists
                    if item.product:
                        current_app.logger.info(
                            f"Item {item.id}: Product {item.product_id} "
                            f"({item.product.name if item.product else 'Unknown'}), "
                            f"Quantity: {item.quantity}, "
                            f"Created: {item.created_at}"
                        )
                    else:
                        current_app.logger.error(f"Product not found for cart item {item.id}")
            else:
                # Check session
                from flask import session
                current_app.logger.warning(f"No items found in cart. Session ID: {session.get('_id', 'No session')}")
                
                # Verify database connection and cart state
                try:
                    # Test database connection
                    check_sql = text("SELECT 1")
                    db.session.execute(check_sql).scalar()
                    current_app.logger.info("Database connection verified")

                    # Double check cart state
                    cart_check_sql = text("""
                        SELECT COUNT(*) FROM cart_items
                        WHERE user_id = :user_id AND deleted_at IS NULL
                    """)
                    cart_count = db.session.execute(
                        cart_check_sql,
                        {"user_id": user_id}
                    ).scalar()
                    
                    current_app.logger.info(f"Direct cart check found {cart_count} items")
                    
                except Exception as e:
                    current_app.logger.error(f"Database verification failed: {str(e)}")
                    current_app.logger.error("Stack trace:", exc_info=True)
            
            return cart_items
            
        except Exception as e:
            current_app.logger.error(f"Error retrieving cart: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            return []
    
    @staticmethod
    def get_cart_total(user_id):
        """Calculate total price of all items in cart"""
        from flask import current_app
        
        try:
            # Use direct SQL query for efficient calculation of active items
            sql = text("""
                SELECT
                    COUNT(*) as count,
                    COALESCE(ROUND(SUM(ci.quantity * p.price * 23000) + 30000, -3), 0) as total
                FROM cart_items ci
                JOIN products p ON ci.product_id = p.id
                WHERE ci.user_id = :user_id
                    AND ci.deleted_at IS NULL
                    AND p.price > 0
            """)
            
            result = db.session.execute(sql, {"user_id": user_id}).first()
            if result:
                current_app.logger.info(f"""
                Cart Total Calculation Result:
                - Active Items: {result.count}
                - Subtotal Value: {result.total - 30000:,} VND
                - Shipping Cost: 30,000 VND
                - Total Value (with shipping): {result.total:,} VND
                - User ID: {user_id}
                """)
                return float(result.total) if result.total is not None else 0.0
            else:
                current_app.logger.warning(f"No active cart items found for user {user_id}")
                return 0.0
            
        except Exception as e:
            current_app.logger.error(f"""
            === Cart Total Calculation Error ===
            Error Type: {type(e).__name__}
            Error Message: {str(e)}
            User ID: {user_id}
            """)
            
            # Log stack trace for debugging
            current_app.logger.error("Stack trace:", exc_info=True)
            current_app.logger.info("Attempting ORM fallback method...")
            
            # Fallback to ORM method with explicit error handling
            try:
                cart_items = CartItem.query.filter_by(
                    user_id=user_id,
                    deleted_at=None
                ).all()
                
                if not cart_items:
                    current_app.logger.warning(f"No active cart items found for user {user_id} (ORM check)")
                    return 0.0
                
                # Calculate total in USD
                subtotal = sum(item.subtotal for item in cart_items if item.product)
                current_app.logger.info(f"Cart subtotal (USD): ${subtotal:,.2f}")
                
                # Convert to VND and round to nearest 1000
                # Add 30,000 VND shipping cost
                total_vnd = round((subtotal * 23000) + 30000, -3)
                current_app.logger.info(f"Cart total (VND): {total_vnd:,} VND")
                
                return float(total_vnd)
                
            except Exception as orm_error:
                current_app.logger.error(f"""
                === ORM Fallback Failed ===
                Error: {str(orm_error)}
                User ID: {user_id}
                """)
                current_app.logger.error("ORM fallback stack trace:", exc_info=True)
                return 0.0
    
    @staticmethod
    def add_to_cart(user_id, product_id, quantity=1):
        """Add a product to cart or update quantity if already exists"""
        try:
            # First check for existing active item
            cart_item = CartItem.query.filter_by(
                user_id=user_id,
                product_id=product_id,
                deleted_at=None
            ).first()
            
            if cart_item:
                current_app.logger.info(f"Updating quantity of existing cart item {cart_item.id}")
                cart_item.quantity += quantity
            else:
                # Check for soft-deleted item
                deleted_item = CartItem.query.filter_by(
                    user_id=user_id,
                    product_id=product_id
                ).first()
                
                if deleted_item:
                    current_app.logger.info(f"Reactivating deleted cart item {deleted_item.id}")
                    deleted_item.deleted_at = None
                    deleted_item.quantity = quantity
                    cart_item = deleted_item
                else:
                    current_app.logger.info(f"Creating new cart item for user {user_id}")
                    cart_item = CartItem(
                        user_id=user_id,
                        product_id=product_id,
                        quantity=quantity
                    )
                    db.session.add(cart_item)
            
            db.session.commit()
            return cart_item
            
        except Exception as e:
            current_app.logger.error(f"Error adding to cart: {str(e)}")
            db.session.rollback()
            return None
    
    @staticmethod
    def update_quantity(user_id, product_id, quantity):
        """Update quantity of a cart item"""
        try:
            # Look for active cart item
            cart_item = CartItem.query.filter_by(
                user_id=user_id,
                product_id=product_id,
                deleted_at=None
            ).first()
            
            if cart_item:
                if quantity > 0:
                    current_app.logger.info(f"Updating cart item {cart_item.id} quantity from {cart_item.quantity} to {quantity}")
                    cart_item.quantity = quantity
                    cart_item.updated_at = datetime.utcnow()
                    db.session.commit()
                    return cart_item
                else:
                    current_app.logger.info(f"Quantity is 0, soft deleting cart item {cart_item.id}")
                    return Cart.remove_from_cart(user_id, product_id)
            else:
                # Check if item exists but is deleted
                deleted_item = CartItem.query.filter_by(
                    user_id=user_id,
                    product_id=product_id
                ).first()
                
                if deleted_item:
                    current_app.logger.info(f"Reactivating deleted cart item {deleted_item.id}")
                    deleted_item.deleted_at = None
                    deleted_item.quantity = quantity
                    deleted_item.updated_at = datetime.utcnow()
                    db.session.commit()
                    return deleted_item
                    
                current_app.logger.warning(f"No cart item found for user {user_id}, product {product_id}")
                return None
                
        except Exception as e:
            current_app.logger.error(f"Error updating cart quantity: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            db.session.rollback()
            return None
    
    @staticmethod
    def remove_from_cart(user_id, product_id):
        """Soft delete a product from cart"""
        try:
            cart_item = CartItem.query.filter_by(
                user_id=user_id,
                product_id=product_id,
                deleted_at=None
            ).first()
            
            if cart_item:
                current_app.logger.info(f"Soft deleting cart item {cart_item.id}")
                cart_item.deleted_at = datetime.utcnow()
                db.session.commit()
                return True
            else:
                current_app.logger.warning(f"No active cart item found for user {user_id}, product {product_id}")
                return False
        except Exception as e:
            current_app.logger.error(f"Error removing item from cart: {str(e)}")
            db.session.rollback()
            return False
    
    @staticmethod
    def clear_cart(user_id):
        """Soft delete all items from cart"""
        try:
            items = CartItem.query.filter_by(
                user_id=user_id,
                deleted_at=None
            ).all()
            
            if items:
                current_app.logger.info(f"Soft deleting {len(items)} items from cart")
                now = datetime.utcnow()
                for item in items:
                    item.deleted_at = now
                db.session.commit()
                return True
            return True
        except Exception as e:
            current_app.logger.error(f"Error clearing cart: {str(e)}")
            db.session.rollback()
            return False