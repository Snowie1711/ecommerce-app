from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Product, Category, ProductImage
from routes.auth import admin_required
from werkzeug.utils import secure_filename
from sqlalchemy import or_
import os
from datetime import datetime

products_bp = Blueprint('products', __name__)

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
    # Handle multiple images
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
    search=None,
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

    if search:
        search_terms = search.split()
        for term in search_terms:
            search_term = f'%{term.lower()}%'
            query = query.filter(
                or_(
                    Product.name.ilike(search_term),
                    Product.description.ilike(search_term)
                )
            )
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    if in_stock is not None:
        query = query.filter(Product.stock > 0 if in_stock else Product.stock == 0)

    return query.options(db.joinedload(Product.images))

@products_bp.route('/products')
def index():
    page = request.args.get('page', 1, type=int)
    categories = request.args.getlist('categories')
    search = request.args.get('search')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock', type=int)
    
    query = get_filtered_query(
        categories=categories,
        search=search,
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
        search=search,
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
    search = request.args.get('search')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    in_stock = request.args.get('in_stock', type=int)
    
    query = get_filtered_query(
        categories=category_name,
        search=search,
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
        search=search,
        min_price=min_price,
        max_price=max_price,
        in_stock=in_stock
    )

@products_bp.route('/<int:id>')
def detail(id):
    # Get product with category and images
    try:
        # Only allow viewing active products for non-admin users
        query = Product.query
        if not (current_user.is_authenticated and current_user.is_admin):
            query = query.filter_by(is_active=True)
            
        product = query.options(
            db.joinedload(Product.category),
            db.joinedload(Product.images)
        ).get_or_404(id, description='The product you are looking for may have been removed or is no longer available. Please try searching for similar products.')
        
        # Check if product is active or if user is admin
        if not product.is_active and (not current_user.is_authenticated or not current_user.is_admin):
            flash('This product is no longer available. Please check our other products.', 'error')
            return redirect(url_for('products.index'))
            
        return render_template('products/detail.html', product=product)
    except Exception as e:
        current_app.logger.error(f"Error accessing product {id}: {str(e)}")
        raise

@products_bp.route('/admin/products')
@login_required
@admin_required
def admin_products():
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category')
    sort = request.args.get('sort', 'name')
    
    query = Product.query.options(
        db.joinedload(Product.category),
        db.joinedload(Product.images)
    )
    
    if category:
        query = query.join(Product.category).filter(
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
    
    categories = Category.query.order_by(Category.name).all()
    
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
                         categories=categories,
                         category=category,
                         sort=sort)

@products_bp.route('/admin/products/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_product():
    if request.method == 'POST':
        data = request.form
        
        product = Product(
            name=data['name'],
            description=data['description'],
            price=int(float(data['price'])),  # Convert to int for VND (no decimals)
            stock=int(data['stock']),
            category_id=int(data['category_id']),
            sku=data['sku'],
            is_active=bool(int(data.get('is_active', 0)))
        )
        
        db.session.add(product)
        db.session.flush()  # Get product ID without committing
        
        try:
            handle_product_images(product, request.files)
            db.session.commit()
            flash('Product created successfully!', 'success')
            return redirect(url_for('products.admin_products'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating product', 'error')
    
    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories)

@products_bp.route('/admin/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.options(
        db.joinedload(Product.images)
    ).get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        
        product.name = data['name']
        product.description = data['description']
        product.price = int(float(data['price']))  # Convert to int for VND (no decimals)
        product.stock = int(data['stock'])
        product.category_id = int(data['category_id'])
        product.sku = data['sku']
        product.is_active = bool(int(data.get('is_active', 0)))
        
        try:
            # Handle image deletions
            images_to_keep = request.form.getlist('existing_images')
            for image in product.images[:]:
                if str(image.id) not in images_to_keep:
                    delete_product_image(image)
            
            # Handle new images
            handle_product_images(product, request.files, 
                               existing_primary=any(img.is_primary for img in product.images))
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('products.admin_products'))
        except Exception as e:
            db.session.rollback()
            flash('Error updating product', 'error')
    
    categories = Category.query.all()
    return render_template('admin/product_form.html',
                         product=product,
                         categories=categories)

@products_bp.route('/admin/products/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.options(
        db.joinedload(Product.images)
    ).get_or_404(id)
    
    # Delete all associated images
    for image in product.images:
        delete_product_image(image)
    
    db.session.delete(product)
    try:
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error deleting product', 'error')
    
    return redirect(url_for('products.admin_products'))

@products_bp.route('/admin/products/<int:id>/images/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(id, image_id):
    product = Product.query.get_or_404(id)
    image = ProductImage.query.get_or_404(image_id)
    
    if image.product_id != product.id:
        return jsonify({'error': 'Image does not belong to this product'}), 400
    
    try:
        was_primary = image.is_primary
        delete_product_image(image)
        
        # If we deleted the primary image, make another image primary
        if was_primary and product.images:
            product.images[0].is_primary = True
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error deleting image'}), 500

@products_bp.route('/admin/products/<int:id>/images/<int:image_id>/make-primary', methods=['POST'])
@login_required
@admin_required
def make_image_primary(id, image_id):
    product = Product.query.get_or_404(id)
    image = ProductImage.query.get_or_404(image_id)
    
    if image.product_id != product.id:
        return jsonify({'error': 'Image does not belong to this product'}), 400
    
    try:
        # Set all images as non-primary
        for img in product.images:
            img.is_primary = (img.id == image_id)
        
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Error updating primary image'}), 500