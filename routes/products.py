from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app
from flask_login import login_required, current_user
from models import db, Product, Category, ProductImage, ProductSize
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
    # Get product with category and images
    try:
        # First get the product with all needed relationships
        product = Product.query.options(
            db.joinedload(Product.category),
            db.joinedload(Product.images),
            db.joinedload(Product.colors)
        ).get_or_404(id, description='The product you are looking for may have been removed or is no longer available. Please try searching for similar products.')
        
        # Then check if it's active for non-admin users
        if not product.is_active and (not current_user.is_authenticated or not current_user.is_admin):
            flash('This product is no longer available. Please check our other products.', 'error')
            return redirect(url_for('products.index'))
            
        return render_template('products/detail.html', product=product, min=min)
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
        category = Category.query.get(int(data['category_id']))
        has_sizes = category.has_sizes if category else False
        
        # Create product
        product = Product(
            name=data['name'],
            description=data['description'],
            price=int(float(data['price'])) if float(data['price']) >= 0 else 0,  # Ensure non-negative price for VND
            stock=0 if has_sizes else int(data['stock']),
            category_id=int(data['category_id']),
            sku=data['sku'],
            is_active=bool(int(data.get('is_active', 0))),
            has_sizes=has_sizes
        )
        
        db.session.add(product)
        db.session.flush()  # Get product ID without committing

        # Handle colors if present
        color_names = request.form.getlist('color_names[]')
        color_codes = request.form.getlist('color_codes[]')
        color_stocks = request.form.getlist('color_stocks[]')
        
        if color_names and color_codes and color_stocks:
            total_color_stock = 0
            for name, code, stock in zip(color_names, color_codes, color_stocks):
                if name and code:
                    stock_value = int(stock or 0)
                    total_color_stock += stock_value
                    color = ProductColor(
                        product=product,
                        color_name=name,
                        color_code=code,
                        stock=stock_value
                    )
                    db.session.add(color)
            product.stock = total_color_stock
        try:
            # Handle product images
            handle_product_images(product, request.files)
            
            # Handle sizes if applicable
            # Handle sizes if applicable
            if has_sizes:
                sizes = request.form.getlist('sizes[]')
                stocks = request.form.getlist('size_stocks[]')
                total_stock = 0
                
                for size, stock in zip(sizes, stocks):
                    if size and stock:
                        stock_value = int(stock)
                        total_stock += stock_value
                        size_entry = ProductSize(
                            product=product,
                            size=size,
                            stock=stock_value
                        )
                        db.session.add(size_entry)
                
                # Update total stock (override color stock if both present)
                product.stock = total_stock
            
            db.session.commit()
            flash('Product created successfully!', 'success')
            return redirect(url_for('products.admin_products'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating product', 'error')
    
    categories = Category.query.all()
    return render_template(
        'admin/product_form.html',
        categories=categories
    )

@products_bp.route('/admin/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.options(
        db.joinedload(Product.images)
    ).get_or_404(id)
    
    if request.method == 'POST':
        data = request.form
        category = Category.query.get(int(data['category_id']))
        has_sizes = category.has_sizes if category else False

        # Validate price is not negative and preserve decimal places
        try:
            price_float = float(data['price'])
            if price_float < 0:
                flash('Price cannot be negative.', 'error')
                categories = Category.query.all()
                sizes = product.sizes if product and product.has_sizes else []
                return render_template('admin/product_form.html',
                    product=product,
                    categories=categories,
                    sizes=sizes
                )
            new_price = int(price_float)  # Convert to integer after validation
        except ValueError:
            flash('Invalid price format.', 'error')
            categories = Category.query.all()
            sizes = product.sizes if product and product.has_sizes else []
            return render_template('admin/product_form.html',
                product=product,
                categories=categories,
                sizes=sizes
            )
        
        product.name = data['name']
        product.description = data['description']
        product.price = new_price  # Convert to int for VND (no decimals)
        
        # Handle base stock for non-sized products without colors
        if not has_sizes and not data.getlist('color_names[]'):
            try:
                product.stock = int(data.get('stock', 0))
            except ValueError:
                product.stock = 0
        product.category_id = int(data['category_id'])
        product.sku = data['sku']
        product.is_active = bool(int(data.get('is_active', 0)))
        product.has_sizes = has_sizes
        
        # Start a transaction for the update
        try:
            # Handle image deletions
            images_to_keep = request.form.getlist('existing_images')
            for image in product.images[:]:
                if str(image.id) not in images_to_keep:
                    delete_product_image(image)
            
            # Handle new images
            handle_product_images(product, request.files,
                                existing_primary=any(img.is_primary for img in product.images))
            
            # Remove existing colors
            for color in product.colors[:]:
                db.session.delete(color)
                
            # Add new colors
            color_names = request.form.getlist('color_names[]')
            color_codes = request.form.getlist('color_codes[]')
            color_stocks = request.form.getlist('color_stocks[]')
            
            if color_names and color_codes and color_stocks:
                total_color_stock = 0
                for name, code, stock in zip(color_names, color_codes, color_stocks):
                    if name and code:
                        try:
                            stock_value = int(stock or 0)
                            if stock_value < 0:
                                stock_value = 0
                            total_color_stock += stock_value
                            color = ProductColor(
                                product=product,
                                color_name=name,
                                color_code=code,
                                stock=stock_value
                            )
                            db.session.add(color)
                        except ValueError:
                            continue
                if not has_sizes:  # Only update total stock if product doesn't have sizes
                    product.stock = total_color_stock
            
            # Handle sizes if applicable
            if has_sizes:
                # Remove existing sizes
                for size in product.sizes[:]:
                    db.session.delete(size)
                
                # Add new sizes
                sizes = request.form.getlist('sizes[]')
                stocks = request.form.getlist('size_stocks[]')
                total_stock = 0
                
                for size, stock in zip(sizes, stocks):
                    if size and stock:
                        try:
                            stock_value = int(stock)
                            if stock_value < 0:
                                stock_value = 0
                            total_stock += stock_value
                            size_entry = ProductSize(
                                product=product,
                                size=size,
                                stock=stock_value
                            )
                            db.session.add(size_entry)
                        except ValueError:
                            continue
                
                # Always update total stock for sized products
                product.stock = total_stock
            
            # Commit all changes in one transaction
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('products.admin_products'))
            
        except Exception as e:
            # Rollback transaction on error
            db.session.rollback()
            current_app.logger.error(f'Error updating product {id}: {str(e)}')
            flash('Error updating product. Please try again.', 'error')
            return render_template('admin/product_form.html',
                product=product,
                categories=Category.query.all(),
                sizes=product.sizes if product.has_sizes else []
            )
    categories = Category.query.all()
    sizes = product.sizes if product and product.has_sizes else []
    return render_template('admin/product_form.html',
        product=product,
        categories=categories,
        sizes=sizes
    )

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

@products_bp.route('/api/products/<int:id>/stock')
def get_product_stock(id):
    """Get available stock for a product with specific size/color"""
    try:
        product = Product.query.get_or_404(id)
        size = request.args.get('size')
        color_id = request.args.get('color_id')
        
        stock = 0
        if product.has_sizes and size:
            size_obj = next((s for s in product.sizes if s.size == size), None)
            if size_obj:
                stock = size_obj.stock
        elif product.colors and color_id:
            try:
                color_id = int(color_id)
                color = next((c for c in product.colors if c.id == color_id), None)
                if color:
                    stock = color.stock
            except (ValueError, TypeError):
                pass
        else:
            stock = product.stock
            
        return jsonify({'stock': stock})
    except Exception as e:
        current_app.logger.error(f"Error getting product stock: {str(e)}")
        return jsonify({'error': 'Error getting stock information'}), 500

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