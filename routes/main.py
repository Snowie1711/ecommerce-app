from flask import Blueprint, render_template, request, jsonify
from models.product import Product
from models.order import OrderItem
from models.category import Category
from sqlalchemy import func, desc, and_, or_
from app import db
from sqlalchemy.sql import text

main_bp = Blueprint('main', __name__)

def get_popular_products(category_id=None, limit=8):
    # Query to get the most ordered products
    query = db.session.query(
        Product,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.count(OrderItem.id).label('order_count')
    ).join(OrderItem).group_by(Product.id)
    
    # Filter by category if specified
    if category_id:
        query = query.filter(Product.category_id == category_id)
    
    # Only include active products
    query = query.filter(Product.is_active == True)
    
    # Order by total quantity sold and number of orders
    popular_products = query.order_by(
        desc('total_quantity'),
        desc('order_count')
    ).limit(limit).all()
    
    # Extract just the product objects
    return [item[0] for item in popular_products]

def get_discounted_products(limit=8):
    """Get products that have a discount price set"""
    return Product.query.filter(
        and_(
            Product.is_active == True,
            Product.discount_price.isnot(None),
            Product.discount_price > 0
        )
    ).order_by(desc(Product.discount_price)).limit(limit).all()

@main_bp.route('/')
def home():
    # Get category_id from query params for filtering
    category_id = request.args.get('category_id', type=int)
    
    # Get featured products (most recent active products)
    featured_products = Product.query.filter_by(is_active=True)\
        .order_by(Product.created_at.desc())\
        .limit(8)\
        .all()
    
    # Get popular products
    popular_products = get_popular_products(category_id=category_id)
    
    # Get discounted products
    discounted_products = get_discounted_products()
    
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
                         popular_products=popular_products,
                         discounted_products=discounted_products,
                         categories=categories,
                         selected_category_id=category_id)

@main_bp.route('/search')
def search():
    query = request.args.get('q', '').strip()
    
    if not query:
        return render_template('search.html', products=[], search_query='')
    
    # Case-insensitive search for products by name
    products = Product.query.filter(
        and_(
            Product.is_active == True,
            or_(
                Product.name.ilike(f'%{query}%'),
                Product.description.ilike(f'%{query}%')
            )
        )
    ).order_by(Product.name).all()
    
    return render_template('search.html', 
                         products=products,
                         search_query=query)

@main_bp.route('/api/search/suggestions')
def search_suggestions():
    query = request.args.get('q', '').strip()
    
    if not query:
        return jsonify([])
        
    # Search for active products matching the query
    products = Product.query.filter(
        and_(
            Product.is_active == True,
            or_(
                Product.name.ilike(f'{query}%'),  # Starts with query
                Product.name.ilike(f'% {query}%')  # Words starting with query
            )
        )
    ).limit(10).all()
    
    suggestions = [
        {
            'id': p.id,
            'name': p.name,
            'price': p.price_display,
            'image': p.image_url_or_placeholder,
            'url': f'/products/{p.id}'
        }
        for p in products
    ]
    
    return jsonify(suggestions)
