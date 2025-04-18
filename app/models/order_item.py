from flask_sqlalchemy import db

class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    variant_id = db.Column(db.Integer, db.ForeignKey('product_variant.id'), nullable=True)
    color_id = db.Column(db.Integer, db.ForeignKey('product_colors.id'), nullable=True)
    size = db.Column(db.String(20), nullable=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)
    price = db.Column(db.Float, nullable=False)
    
    # Add the matching order relationship to correspond with Order.items
    order = db.relationship('Order', back_populates='items', lazy=True)
    
    # Updated product relationship to match what's in your original model
    product = db.relationship('Product', back_populates='order_items', lazy=True)
    
    # Keep color relationship as in your original model
    color = db.relationship('ProductColor', lazy=True)
    
    # Add the variant relationship (making it consistent with the others)
    variant = db.relationship('ProductVariant', lazy=True)
    
    def __repr__(self):
        return f'<OrderItem {self.id}>'
