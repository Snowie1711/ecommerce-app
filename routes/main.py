from flask import Blueprint, render_template
from models.product import Product
from models.category import Category

bp = Blueprint('main', __name__)

@bp.route('/')
def home():
    # Get featured products (for example, the 8 most recent active products)
    featured_products = Product.query.filter_by(is_active=True)\
        .order_by(Product.created_at.desc())\
        .limit(8)\
        .all()
    
    # Get all categories with their product counts
    categories = []
    for category in Category.query.order_by(Category.name).all():
        product_count = Product.query.filter_by(
            category_id=category.id,
            is_active=True
        ).count()
        
        if product_count > 0:  # Only show categories with active products
            categories.append({
                "id": category.id,
                "name": category.name,
                "product_count": product_count
            })
    
    return render_template('home.html',
                         featured_products=featured_products,
                         categories=categories)