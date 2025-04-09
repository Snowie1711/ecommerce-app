from . import db
from datetime import datetime

class ProductSize(db.Model):
    __tablename__ = 'product_sizes'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size = db.Column(db.String(10), nullable=False)  # XS, S, M, L, XL, etc.
    stock = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    product = db.relationship('Product', back_populates='sizes')
    
    def update_stock(self, quantity):
        """
        Update size stock
        :param quantity: int (positive for restocking, negative for reducing stock)
        :return: bool (True if update successful, False if insufficient stock)
        """
        new_stock = self.stock + quantity
        if new_stock < 0:
            return False
        self.stock = new_stock
        return True

    def __repr__(self):
        return f'<ProductSize {self.product.name} - {self.size}>'