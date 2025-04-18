from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Product, Category, ProductImage, ProductSize, Review
from routes.auth import admin_required
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import os
from datetime import datetime

products_bp = Blueprint('products', __name__, url_prefix='/products')

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_image(file):
    """Helper function to save an image and return the filename"""
    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            
            # Ensure upload directory exists
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            
            # Save the file
            file.save(filepath)
            
            # Set proper permissions
            os.chmod(filepath, 0o644)
            
            return filename
        except Exception as e:
            current_app.logger.error(f"Error saving image: {str(e)}")
            return None
    return None

def handle_product_images(product, files, existing_primary=None):
    """Helper function to handle multiple image uploads for a product"""
    uploaded_files = files.getlist('images')
    primary_image_id = request.form.get('primary_image')
    
    for file in uploaded_files:
        if file and allowed_file(file.filename):
            filename = save_image(file)
            if filename:
                image = ProductImage(
                    product_id=product.id,
                    image_url=filename,
                    is_primary=False  # Will set primary later
                )
                db.session.add(image)
    
    # If this is first upload, make first image primary
    if not existing_primary and uploaded_files:
        first_image = product.images[0] if product.images else None
        if first_image:
            first_image.is_primary = True

    # Update primary image if specified
    if primary_image_id:
        # First, set all images as non-primary
        for image in product.images:
            image.is_primary = (str(image.id) == primary_image_id)

def delete_product_image(image):
    """Helper function to delete a product image file and record"""
    if image.image_url:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(image)

def get_filtered_query(
    categories=None,
    min_price=None,
    max_price=None,
    in_stock=None
):
    query = Product.query.filter_by(is_active=True)

    if categories:
        if isinstance(categories, str):
            query = query.join(Product.category).filter(
                db.func.lower(Category.name) == db.func.lower(categories)
            )
        else:
            query = query.join(Product.category).filter(
                db.func.lower(Category.name).in_([cat.lower() for cat in categories])
            )
        query = query.options(db.contains_eager(Product.category))
    else:
        query = query.options(db.joinedload(Product.category))

    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is not None:
        if str(in_stock) == '1':
            query = query.filter(Product.stock > 0)
        elif str(in_stock) == '0':
            query = query.filter(Product.stock == 0)

    return query.options(db.joinedload(Product.images))

@products_bp.route('/products')
def index():
    page = request.args.get('page', 1, type=int)
    categories = request.args.getlist('categories')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock', type=int)
    
    query = get_filtered_query(
        categories=categories,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock
    )
    
    products = query.paginate(
        page=page,
        per_page=current_app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )
    
    all_categories = Category.query.all()
    
    return render_template(
        'products/index.html',
        products=products,
        categories=all_categories,
        selected_categories=categories,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock
    )

@products_bp.route('/category/<category_name>')
def category_view(category_name):
    category = Category.query.filter(
        db.func.lower(Category.name) == db.func.lower(category_name)
    ).first_or_404()
    
    page = request.args.get('page', 1, type=int)
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock', type=int)
    
    query = get_filtered_query(
        categories=category_name,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock
    )
    
    products = query.paginate(
        page=page,
        per_page=current_app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )
    
    all_categories = Category.query.order_by(Category.name).all()
    
    return render_template(
        'products/category.html',
        products=products,
        categories=all_categories,
        selected_category=category.name,
        category=category,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock
    )

@products_bp.route('/<int:id>')  # Now maps to /products/<id>
def detail(id):
    # Get product with category, images and reviews
    try:
        # First get the product with all needed relationships
        product = Product.query.options(
            db.joinedload(Product.category),
            db.joinedload(Product.images),
            db.joinedload(Product.colors),
            db.joinedload(Product.reviews).joinedload(Review.user)
        ).get_or_404(id, description='The product you are looking for may have been removed or is no longer available. Please try searching for similar products.')
        
        # Then check if it's active for non-admin users
        if not product.is_active and (not current_user.is_authenticated or not current_user.is_admin):
            flash('This product is no longer available. Please check our other products.', 'error')
            return redirect(url_for('products.index'))
        
        # Get reviews sorted by created_at in descending order
        reviews = sorted(product.reviews, key=lambda x: x.created_at, reverse=True)
            
        return render_template('products/detail.html', product=product, reviews=reviews, min=min)
    except Exception as e:
        current_app.logger.error(f"Error accessing product {id}: {str(e)}")
        raise

@products_bp.route('/admin/products')
@login_required
@admin_required
def manage_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    sort = request.args.get('sort', 'name')
    search = request.args.get('search', '')
    
    # Normalize search string
    if search:
        search = ' '.join(search.split())  # Normalize whitespace
        current_app.logger.info(f"Searching for products with term: '{search}'")
    
    # Start with base query
    query = Product.query
    
    # Always join category to avoid multiple queries
    query = query.join(Product.category).options(
        db.joinedload(Product.category),
        db.joinedload(Product.images)
    )
    
    # Apply search filter if provided
    if search:
        search_term = f"%{search}%"
        current_app.logger.info(f"Searching with term: '{search}', SQL LIKE pattern: '{search_term}'")
        query = query.filter(Product.name.ilike(search_term))
        current_app.logger.info(f"Found {query.count()} products matching search term")

    # Apply category filter if provided
    if category:
        query = query.filter(
            db.func.lower(Category.name) == db.func.lower(category)
        )

    if sort == 'name':
        query = query.order_by(Product.name)
    elif sort == 'price':
        query = query.order_by(Product.price)
    elif sort == 'stock':
        query = query.order_by(Product.stock)
    elif sort == 'category':
        query = query.join(Product.category).order_by(Category.name)

    products = query.paginate(
        page=page,
        per_page=current_app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'products': [p.to_dict() for p in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': products.page
        })

    return render_template('admin/products.html',
                        products=products,
                        categories=Category.query.all(),
                        category=category,
                        sort=sort)