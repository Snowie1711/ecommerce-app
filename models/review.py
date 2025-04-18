from datetime import datetime
from extensions import db

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    comment = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    product = db.relationship('Product', back_populates='reviews', lazy=True)
    order = db.relationship('Order', backref=db.backref('reviews', lazy=True))

    # Ensure one review per product per order per user
    __table_args__ = (
        db.UniqueConstraint('user_id', 'product_id', 'order_id', name='unique_review_per_order'),
    )

    def __init__(self, user_id, product_id, order_id, rating, comment):
        self.user_id = user_id
        self.product_id = product_id
        self.order_id = order_id
        self.rating = rating
        self.comment = comment

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'product_id': self.product_id,
            'order_id': self.order_id,
            'rating': self.rating,
            'comment': self.comment,
            'created_at': self.created_at.isoformat(),
            'user': {
                'id': self.user.id,
                'name': f"{self.user.first_name} {self.user.last_name}".strip()
            }
        }