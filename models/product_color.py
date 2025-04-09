from . import db
from datetime import datetime

class ProductColor(db.Model):
    __tablename__ = 'product_colors'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    color_name = db.Column(db.String(50), nullable=False)  # e.g., "Red", "Blue", etc.
    color_code = db.Column(db.String(7), nullable=False)   # Hex code e.g., "#FF0000"
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    product = db.relationship('Product', back_populates='colors')
    
    def update_stock(self, quantity):
        """
        Update color stock
        :param quantity: int (positive for restocking, negative for reducing stock)
        :return: bool (True if update successful, False if insufficient stock)
        """
        new_stock = self.stock + quantity
        if new_stock < 0:
            return False
        self.stock = new_stock
        return True

    def __repr__(self):
        return f'<ProductColor {self.product.name} - {self.color_name}>'