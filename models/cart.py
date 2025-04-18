from extensions import db
from datetime import datetime
from flask import current_app

class CartItem(db.Model):
    """Cart model for storing user cart items"""
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    size = db.Column(db.String(10), nullable=True)  # For sized products
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.id'), nullable=True)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = db.Column(db.DateTime, nullable=True)  # Soft delete column
    
    # Relationships
    product = db.relationship('Product', lazy=True)
    variant = db.relationship('ProductVariant', lazy=True)
    
    @classmethod
    def get_cart_for_user(cls, user_id):
        """
        Get the complete cart information for a user
        
        Args:
            user_id: Can be either an integer (authenticated user) or string (anonymous user)
            
        Returns a dictionary with cart items and totals
        """
        try:
            if not user_id:
                current_app.logger.error("get_cart_for_user called with empty user_id")
                raise ValueError("User ID is required")

            # Convert string user_id to int if it's a numeric string
            try:
                user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            except ValueError as e:
                current_app.logger.error(f"Invalid user_id format: {user_id}")
                raise ValueError(f"Invalid user ID format: {str(e)}")

            # Get all active cart items for this user
            cart_items = cls.query.filter_by(user_id=user_id, deleted_at=None).all()
            
            # Calculate totals and build cart dict
            items = []
            subtotal = 0
            
            for item in cart_items:
                product = item.product
                # Skip if product doesn't exist or is inactive
                if not product or not product.is_active:
                    continue
                    
                # Use discounted price if available
                price = product.discount_price if product.discount_price else product.price
                item_subtotal = price * item.quantity
                subtotal += item_subtotal
                
                # Build item dict
                item_dict = {
                    'id': item.id,
                    'product_id': product.id,
                    'name': product.name,
                    'price': price,
                    'original_price': product.price,
                    'quantity': item.quantity,
                    'subtotal': item_subtotal,
                    'image_url': product.primary_image.image_url if product.primary_image else product.image_url,
                    'size': item.size,
                    'color_id': item.color_id,
                    'sku': product.sku,
                    'inventory_type': product.inventory_type
                }
                
                # Handle stock based on inventory type
                if product.inventory_type == 'both' and item.variant_id:
                    variant = next((v for v in product.variants if v.id == item.variant_id), None)
                    if variant:
                        item_dict['stock'] = variant.stock
                        item_dict['variant'] = {
                            'id': variant.id,
                            'size': variant.size.size,
                            'color_name': variant.color.color_name,
                            'color_code': variant.color.color_code,
                            'stock': variant.stock
                        }
                elif product.inventory_type == 'color' and item.color_id:
                    color = next((c for c in product.colors if c.id == item.color_id), None)
                    if color:
                        item_dict['stock'] = color.stock
                        item_dict['color'] = {
                            'id': color.id,
                            'name': color.color_name,
                            'code': color.color_code,
                            'stock': color.stock
                        }
                elif product.inventory_type == 'size' and item.size:
                    size_obj = next((s for s in product.sizes if s.size == item.size), None)
                    if size_obj:
                        item_dict['stock'] = size_obj.stock
                        item_dict['size_info'] = {
                            'size': size_obj.size,
                            'stock': size_obj.stock
                        }
                else:
                    item_dict['stock'] = product.stock
                
                items.append(item_dict)
            
            # Set shipping cost to 0 (free shipping)
            shipping_cost = 0
            
            # Total is now just the subtotal since shipping is free
            total = subtotal
            
            return {
                'items': items,
                'subtotal': subtotal,
                'shipping_cost': shipping_cost,
                'total': total,
                'item_count': len(items)
            }
            
        except ValueError as e:
            # Re-raise ValueError for invalid user_id
            raise
        except Exception as e:
            # Log the full stack trace for debugging
            current_app.logger.error(f"Error getting cart for user {user_id}: {str(e)}")
            current_app.logger.error("Stack trace:", exc_info=True)
            
            # Return empty cart rather than raising exception to frontend
            return {
                'items': [],
                'subtotal': 0,
                'shipping_cost': 0,
                'total': 0,
                'item_count': 0,
                'error': 'An error occurred while retrieving your cart'
            }

    @classmethod
    def clear_cart(cls, user_id):
        """
        Remove all items from a user's cart
        
        Args:
            user_id: Can be either an integer (authenticated user) or string (anonymous user)
        """
        try:
            # Convert string user_id to int if it's a numeric string
            try:
                user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            except ValueError:
                pass
                
            # Use soft delete by setting deleted_at timestamp
            cart_items = cls.query.filter_by(user_id=user_id, deleted_at=None).all()
            for item in cart_items:
                item.deleted_at = datetime.utcnow()
            db.session.commit()
            return True
        except Exception as e:
            current_app.logger.error(f"Error clearing cart: {str(e)}")
            db.session.rollback()
            return False
            
    @classmethod
    def add_to_cart(cls, user_id, product_id, quantity=1, size=None, color_id=None, variant_id=None):
        """
        Add a product to cart or update quantity if already exists
        
        Args:
            user_id: Can be either an integer (authenticated user) or string (anonymous user)
            product_id: ID of the product to add
            quantity: Amount to add (default: 1)
            size: Optional size selection
            color_id: Optional color selection
            variant_id: Optional variant selection
            
        Returns:
            dict: Status and message
        """
        try:
            # Convert string user_id to int if it's a numeric string
            try:
                user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            except ValueError:
                pass
                
            from models.product import Product
            product = Product.query.get(product_id)
            if not product:
                return {"success": False, "message": "Product not found"}
            
            # Use provided variant_id directly if given
            if variant_id:
                # Verify the variant exists and is valid
                from models.product import ProductVariant
                variant = ProductVariant.query.get(variant_id)
                if not variant or variant.product_id != product.id:
                    return {"success": False, "message": "Selected variant not available"}
                if variant.stock < quantity:
                    return {"success": False, "message": "Not enough stock available"}
            elif product.inventory_type == 'both' and size and color_id:
                # Find matching variant if not provided directly
                matching_variant = next(
                    (v for v in product.variants
                     if v.size.size == size and v.color.id == color_id),
                    None
                )
                if not matching_variant:
                    return {"success": False, "message": "Selected variant not available"}
                variant_id = matching_variant.id
                if matching_variant.stock < quantity:
                    return {"success": False, "message": "Not enough stock available"}
            
            # Check if product exists in cart
            cart_item = cls.query.filter_by(
                user_id=user_id,
                product_id=product_id,
                size=size,
                color_id=color_id,
                variant_id=variant_id,
                deleted_at=None
            ).first()
            
            if cart_item:
                # Update quantity
                cart_item.quantity += quantity
                db.session.commit()
                return {"success": True, "message": "Cart updated"}
            else:
                # Create new cart item
                new_item = cls(
                    user_id=user_id,
                    product_id=product_id,
                    quantity=quantity,
                    size=size,
                    color_id=color_id,
                    variant_id=variant_id
                )
                db.session.add(new_item)
                db.session.commit()
                return {"success": True, "message": "Product added to cart"}
                
        except Exception as e:
            current_app.logger.error(f"Error adding to cart: {str(e)}")
            db.session.rollback()
            return {"success": False, "message": f"Error: {str(e)}"}
            
    @classmethod
    def update_cart_item(cls, item_id, quantity, user_id):
        """
        Update cart item quantity
        
        Args:
            user_id: Can be either an integer (authenticated user) or string (anonymous user)
            item_id: ID of the cart item to update
            quantity: New quantity to set
            
        Returns:
            dict: Status and message
        """
        try:
            # Convert string user_id to int if it's a numeric string
            try:
                user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            except ValueError:
                pass
                
            cart_item = cls.query.filter_by(id=item_id, user_id=user_id, deleted_at=None).first()
            
            if not cart_item:
                return {"success": False, "message": "Item not found in cart"}
                
            if quantity <= 0:
                # Soft delete if quantity is zero or negative
                cart_item.deleted_at = datetime.utcnow()
                db.session.commit()
                return {"success": True, "message": "Item removed from cart"}
            else:
                # Update quantity
                cart_item.quantity = quantity
                db.session.commit()
                return {"success": True, "message": "Cart updated"}
                
        except Exception as e:
            current_app.logger.error(f"Error updating cart: {str(e)}")
            db.session.rollback()
            return {"success": False, "message": f"Error: {str(e)}"}
    
    @classmethod
    def remove_from_cart(cls, user_id, product_id, size=None, color_id=None):
        """
        Remove a product from cart
        
        Args:
            user_id: Can be either an integer (authenticated user) or string (anonymous user)
            product_id: ID of the product to remove
            size: Optional size to match
            color_id: Optional color ID to match
            
        Returns:
            bool: True if item was removed, False if not found
        """
        try:
            # Convert string user_id to int if it's a numeric string
            try:
                user_id = int(user_id) if isinstance(user_id, str) and user_id.isdigit() else user_id
            except ValueError:
                pass
                
            # Build query to find the cart item
            query = cls.query.filter_by(
                user_id=user_id,
                product_id=product_id,
                deleted_at=None
            )
            
            # Add size filter if provided
            if size:
                query = query.filter_by(size=size)
                
            # Add color filter if provided
            if color_id:
                try:
                    color_id = int(color_id)
                    query = query.filter_by(color_id=color_id)
                except ValueError:
                    return False
            
            # Get the cart item
            cart_item = query.first()
            
            if not cart_item:
                return False
                
            # Soft delete the item
            cart_item.deleted_at = datetime.utcnow()
            db.session.commit()
            return True
            
        except Exception as e:
            current_app.logger.error(f"Error removing from cart: {str(e)}")
            db.session.rollback()
            return False

    def __repr__(self):
        return f'<Cart Item {self.id}: Product {self.product_id}>'


# For backward compatibility with existing code
Cart = CartItem