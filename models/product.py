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
    stock = db.Column(db.Integer, default=0)
    image_url = db.Column(db.String(500))  # Kept for backward compatibility
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    cart_items = db.relationship('CartItem',
                             back_populates='product',
                             lazy=True,
                             cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', back_populates='product', lazy=True)
    images = db.relationship('ProductImage', backref='product', lazy=True, 
                          cascade='all, delete-orphan',
                          order_by='ProductImage.is_primary.desc()')
    category = db.relationship('Category', back_populates='products', lazy=True)
    
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
        return self.stock > 0
    
    def update_stock(self, quantity):
        """
        Update product stock
        :param quantity: int (positive for restocking, negative for reducing stock)
        :return: bool (True if update successful, False if insufficient stock)
        """
        new_stock = self.stock + quantity
        if new_stock < 0:
            return False
        self.stock = new_stock
        return True
    
    @property
    def price_display(self):
        """Get formatted price"""
        return "{:,.0f}".format(self.price)
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'price': self.price,  # Price is already in VND
            'stock': self.stock,
            'image_url': self.primary_image.image_url if self.primary_image else self.image_url,
            'images': [{'id': img.id, 'url': img.image_url, 'is_primary': img.is_primary}
                      for img in self.images] if self.images else [],
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'sku': self.sku,
            'is_active': self.is_active,
            'is_in_stock': self.is_in_stock,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Product {self.name}>'