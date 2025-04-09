from . import db
from datetime import datetime
from sqlalchemy.ext.hybrid import hybrid_property

class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    # Price in VND (Vietnamese Dong)
    price = db.Column(db.Integer, nullable=False)
    discount_price = db.Column(db.Integer, nullable=True)  # Price after discount in VND
    stock = db.Column(db.Integer, default=0)  # Total stock across all sizes for sized products
    image_url = db.Column(db.String(500))  # Kept for backward compatibility
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    has_sizes = db.Column(db.Boolean, default=False)  # Whether product needs sizes (clothing/footwear)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem',
                              back_populates='product',
                              lazy=True,
                              cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', back_populates='product', lazy=True)
    colors = db.relationship('ProductColor', back_populates='product',
                           lazy=True, cascade='all, delete-orphan')
    images = db.relationship('ProductImage', backref='product', lazy=True,
                           cascade='all, delete-orphan',
                           order_by='ProductImage.is_primary.desc()')
    category = db.relationship('Category', back_populates='products', lazy=True)
    sizes = db.relationship('ProductSize', back_populates='product',
                          lazy=True, cascade='all, delete-orphan')
    
    @property
    def primary_image(self):
        """Get the primary image URL or fallback to the first available image"""
        if self.images:
            primary = next((img for img in self.images if img.is_primary), None)
            return primary or self.images[0]
        return None

    @property
    def image_url_or_placeholder(self):
        """Get the image URL with fallback to placeholder"""
        if self.primary_image:
            return self.primary_image.image_url
        if self.image_url:  # Legacy support
            return self.image_url
        return 'images/placeholder.jpg'  # Default placeholder
    @hybrid_property
    def is_in_stock(self):
        if self.has_sizes:
            return any(size.stock > 0 for size in self.sizes)
        elif self.colors:
            return any(color.stock > 0 for color in self.colors)
        return self.stock > 0
    
    def update_stock(self, quantity, size=None, color_id=None):
        """
        Update product stock
        :param quantity: int (positive for restocking, negative for reducing stock)
        :param size: str (size code for sized products)
        :param color_id: int (color ID for products with colors)
        :return: bool (True if update successful, False if insufficient stock)
        """
        if self.has_sizes and size:
            size_obj = next((s for s in self.sizes if s.size == size), None)
            if not size_obj:
                return False
            return size_obj.update_stock(quantity)
        elif color_id:
            color = next((c for c in self.colors if c.id == color_id), None)
            if not color:
                return False
            return color.update_stock(quantity)
        else:
            new_stock = self.stock + quantity
            if new_stock < 0:
                return False
            self.stock = new_stock
            return True
    
    @property
    def price_display(self):
        """Get formatted price"""
        if self.discount_price is not None:
            return "{:,.0f}".format(self.discount_price)
        return "{:,.0f}".format(self.price)
    
    @property
    def original_price_display(self):
        """Get formatted original price"""
        return "{:,.0f}".format(self.price)
    
    @property
    def has_discount(self):
        """Check if product has an active discount"""
        return bool(self.discount_price is not None and self.discount_price < self.price)
        
    @property
    def discount_percentage(self):
        """Calculate discount percentage"""
        if self.has_discount:
            discount = self.price - self.discount_price
            return int((discount / self.price) * 100)
        return 0
    
    def to_dict(self):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,  # Price is already in VND
            'price_display': self.price_display,  # Add formatted price
            'has_discount': self.has_discount,
            'discount_price': self.discount_price,
            'original_price_display': self.original_price_display,
            'stock': self.stock,
            'image_url': self.primary_image.image_url if self.primary_image else self.image_url,
            'images': [{'id': img.id, 'url': img.image_url, 'is_primary': img.is_primary}
                      for img in self.images] if self.images else [],
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'sku': self.sku,
            'is_active': self.is_active,
            'is_in_stock': self.is_in_stock,
            'has_sizes': self.has_sizes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if self.has_sizes:
            data['sizes'] = [
                {
                    'id': size.id,
                    'size': size.size,
                    'stock': size.stock
                }
                for size in self.sizes
            ]
        
        if self.colors:
            data['colors'] = [
                {
                    'id': color.id,
                    'name': color.color_name,
                    'code': color.color_code,
                    'stock': color.stock
                }
                for color in self.colors
            ]
            
        return data
    
    def __repr__(self):
        return f'<Product {self.name}>'