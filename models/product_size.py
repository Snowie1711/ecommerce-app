from extensions import db
from datetime import datetime

class ProductSize(db.Model):
    __tablename__ = 'product_sizes'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    size = db.Column(db.String(20), nullable=False)
    stock = db.Column(db.Integer, nullable=False, default=0)
    
    product = db.relationship('Product', back_populates='sizes')
    variants = db.relationship('ProductVariant', back_populates='size')
    
    def __repr__(self):
        return f'<ProductSize {self.size}>'