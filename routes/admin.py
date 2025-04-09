from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, abort
from flask_login import login_required
from models import db, User, Product, Order, OrderItem, Category, OrderStatus, ProductImage, ProductSize, ProductColor
from routes.auth import admin_required
from sqlalchemy import func
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename
import json
import os

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
            
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            file.save(filepath)
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
                    is_primary=False
                )
                db.session.add(image)
    
    if not existing_primary and uploaded_files:
        first_image = product.images[0] if product.images else None
        if first_image:
            first_image.is_primary = True

    if primary_image_id:
        for image in product.images:
            image.is_primary = (str(image.id) == primary_image_id)

def delete_product_image(image):
    """Helper function to delete a product image file and record"""
    if image.image_url:
        image_path = os.path.join(current_app.config['UPLOAD_FOLDER'], image.image_url)
        if os.path.exists(image_path):
            os.remove(image_path)
    db.session.delete(image)

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Get summary statistics
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    
    # Calculate total revenue
    revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Get low stock products (less than 10 items)
    low_stock = Product.query.filter(Product.stock < 10).all()
    
    return render_template('admin/dashboard.html',
                         total_users=total_users,
                         total_products=total_products,
                         total_orders=total_orders,
                         revenue=revenue,
                         recent_orders=recent_orders,
                         low_stock=low_stock)

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/<int:id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(id):
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    try:
        db.session.commit()
        return jsonify({'status': 'success', 'is_active': user.is_active})
    except:
        db.session.rollback()
        return jsonify({'status': 'error'}), 500

@admin_bp.route('/analytics')
@login_required
@admin_required
def analytics():
    # Get date range from query parameters or default to last 30 days
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=30)
    
    # Sales over time
    sales_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        Order.created_at.between(start_date, end_date)
    ).group_by(
        func.date(Order.created_at)
    ).all()
    
    # Top selling products
    top_products = db.session.query(
        Product.name,
        func.sum(OrderItem.quantity).label('total_quantity'),
        func.sum(OrderItem.quantity * OrderItem.price).label('total_revenue')
    ).join(
        OrderItem
    ).group_by(
        Product.id
    ).order_by(
        func.sum(OrderItem.quantity).desc()
    ).limit(10).all()
    
    # Category distribution
    category_data = db.session.query(
        Category.name.label('category_name'),
        func.count(Product.id).label('product_count')
    ).join(
        Product, Product.category_id == Category.id
    ).group_by(
        Category.id, Category.name
    ).all()
    
    # Format data for charts
    sales_chart_data = {
        'labels': [str(row.date) for row in sales_data],
        'orders': [row.order_count for row in sales_data],
        'revenue': [int(row.revenue) for row in sales_data]  # Revenue is already in VND
    }
    
    products_chart_data = {
        'labels': [row.name for row in top_products],
        'quantities': [row.total_quantity for row in top_products],
        'revenue': [float(row.total_revenue) for row in top_products]
    }
    
    category_chart_data = {
        'labels': [row.category_name for row in category_data],
        'counts': [row.product_count for row in category_data]
    }
    
    return render_template('admin/analytics.html',
                         sales_data=json.dumps(sales_chart_data),
                         products_data=json.dumps(products_chart_data),
                         category_data=json.dumps(category_chart_data))

@admin_bp.route('/orders')
@login_required
@admin_required
def manage_orders():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    query = Order.query
    
    if status:
        query = query.filter_by(status=status)
    
    if start_date:
        try:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(Order.created_at >= start)
        except ValueError:
            pass
    
    if end_date:
        try:
            end = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Order.created_at < end)
        except ValueError:
            pass
    
    orders = query.order_by(Order.created_at.desc()).paginate(page=page, per_page=20)
    return render_template('admin/orders.html', orders=orders, statuses=OrderStatus)

@admin_bp.route('/orders/<int:id>')
@login_required
@admin_required
def order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/order_detail.html', order=order, statuses=OrderStatus)

@admin_bp.route('/orders/<int:id>/update-status', methods=['POST'])
@login_required
@admin_required
def update_order_status(id):
    order = Order.query.get_or_404(id)
    status = request.form.get('status')
    
    try:
        order.status = OrderStatus.from_string(status)
        if status.lower() == OrderStatus.SHIPPED.value:
            order.tracking_number = request.form.get('tracking_number')
        
        try:
            db.session.commit()
            flash('Order status updated successfully!', 'success')
        except:
            db.session.rollback()
            flash('Error updating order status', 'error')
    except ValueError:
        flash('Invalid status', 'error')
    
    return redirect(url_for('admin.order_detail', id=id))

# API endpoints for debugging
@admin_bp.route('/api/debug/products')
@login_required
@admin_required
def debug_products():
    search = request.args.get('search', '')
    products = Product.query.filter(Product.name.ilike(f'%{search}%')).all()
    return jsonify([{
        'id': p.id,
        'name': p.name,
        'category': p.category.name
    } for p in products])

# API endpoints
@admin_bp.route('/api/stats')
@login_required
@admin_required
def api_stats():
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    revenue = db.session.query(func.sum(Order.total_amount)).scalar() or 0
    
    return jsonify({
        'total_users': total_users,
        'total_products': total_products,
        'total_orders': total_orders,
        'total_revenue': int(revenue)  # Revenue is already in VND
    })

@admin_bp.route('/api/sales-data')
@login_required
@admin_required
def api_sales_data():
    days = request.args.get('days', 30, type=int)
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    sales_data = db.session.query(
        func.date(Order.created_at).label('date'),
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_amount).label('revenue')
    ).filter(
        Order.created_at.between(start_date, end_date)
    ).group_by(
        func.date(Order.created_at)
    ).all()
    
    return jsonify([{
        'date': str(row.date),
        'order_count': row.order_count,
        'revenue': float(row.revenue)
    } for row in sales_data])

@admin_bp.route('/users/<int:id>/update-password', methods=['POST'])
@login_required
@admin_required
def update_user_password(id):
    user = User.query.get_or_404(id)
    data = request.get_json()
    
    if not data or 'password' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Password is required'
        }), 400
    
    if len(data['password']) < 6:
        return jsonify({
            'status': 'error',
            'message': 'Password must be at least 6 characters long'
        }), 400
    
    try:
        user.password = data['password']  # Model will handle hashing
        db.session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Password updated successfully'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': 'Error updating password'
        }), 500

@admin_bp.route('/discounts', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_discounts():
    # Get active products excluding those already on sale
    products = Product.query.filter_by(is_active=True).order_by(Product.name).all()
    return render_template('admin/discounts.html', products=products)

@admin_bp.route('/apply-discount', methods=['POST'])
@login_required
@admin_required
def apply_discount():
    product_ids = request.form.getlist('product_ids')
    discount_type = request.form.get('discount_type')
    try:
        discount_value = float(request.form.get('discount_value', 0))
    except ValueError:
        flash('Invalid discount value.', 'error')
        return redirect(url_for('admin.manage_discounts'))
    
    if not product_ids:
        flash('Please select at least one product.', 'error')
        return redirect(url_for('admin.manage_discounts'))
    
    if discount_value <= 0:
        flash('Discount value must be greater than 0.', 'error')
        return redirect(url_for('admin.manage_discounts'))
    
    try:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        
        for product in products:
            if discount_type == 'percentage':
                # Validate percentage (0-100)
                if discount_value > 100:
                    flash('Percentage discount cannot exceed 100%.', 'error')
                    continue
                    
                # Calculate discounted price
                discount_price = int(product.price * (1 - discount_value / 100))
                
                # Ensure minimum price of 1000 VND
                if discount_price < 1000:
                    flash(f'Cannot apply {discount_value}% discount to {product.name} - final price would be too low.', 'error')
                    continue
            else:
                # Fixed amount discount
                if discount_value >= product.price:
                    flash(f'Fixed discount cannot exceed product price for {product.name}.', 'error')
                    continue
                    
                discount_price = int(product.price - discount_value)
            
            # Apply the discount
            product.discount_price = discount_price
            flash(f'Applied discount to {product.name}: {"{:,.0f}".format(product.price)}₫ → {"{:,.0f}".format(discount_price)}₫', 'success')
        
        db.session.commit()
        flash('Discount operation completed.', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash('Error applying discounts.', 'error')
        current_app.logger.error(f'Error applying discounts: {str(e)}')
    
    return redirect(url_for('admin.manage_discounts'))

@admin_bp.route('/remove-discount', methods=['POST'])
@login_required
@admin_required
def remove_discount():
    product_ids = request.form.getlist('product_ids')
    
    if not product_ids:
        flash('Please select at least one product.', 'error')
        return redirect(url_for('admin.manage_discounts'))
    
    try:
        products = Product.query.filter(Product.id.in_(product_ids)).all()
        for product in products:
            if product.discount_price is not None:
                product.discount_price = None
                flash(f'Removed discount from {product.name}', 'success')
        
        db.session.commit()
        flash('Selected discounts have been removed.', 'success')
    except Exception as e:
        db.session.rollback()
        flash('Error removing discounts.', 'error')
        current_app.logger.error(f'Error removing discounts: {str(e)}')
    
    return redirect(url_for('admin.manage_discounts'))

# Product management routes
@admin_bp.route('/products')
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
    # Ensure proper join for category-related operations
    if sort == 'category' or category:
        query = query.join(Product.category)

    # Apply sorting
    if sort == 'name':
        query = query.order_by(Product.name.asc())
    elif sort == 'price':
        query = query.order_by(Product.price.asc())
    elif sort == 'stock':
        query = query.order_by(Product.stock.desc())
    elif sort == 'category':
        query = query.order_by(Category.name.asc())
    else:
        query = query.order_by(Product.name.asc())
    
    
    products = query.paginate(
        page=page,
        per_page=current_app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )
    
    # Get categories for filter dropdown
    categories = Category.query.order_by(Category.name).all()
    
    # Log search parameters for debugging
    current_app.logger.info(f"Search Parameters - Search: {search}, Category: {category}, Sort: {sort}, Page: {page}")
    # Skip AJAX handling for search requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' and not search:
        return jsonify({
            'success': True,
            'products': [p.to_dict() for p in products.items],
            'total': products.total,
            'pages': products.pages,
            'current_page': products.page
        })

    # Add debug log before rendering
    current_app.logger.info("Rendering template with parameters:")
    current_app.logger.info(f"- Search term: '{search}'")
    current_app.logger.info(f"- Found products: {products.total}")
    current_app.logger.info(f"- Current page: {page}")
    
    return render_template('admin/products.html',
                          products=products,
                          categories=categories,
                         category=category,
                         sort=sort,
                         search=search)


@admin_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_product():
    if request.method == 'POST':
        data = request.form
        category = Category.query.get(int(data['category_id']))
        has_sizes = category.has_sizes if category else False
        
        product = Product(
            name=data['name'],
            description=data['description'],
            price=int(float(data['price'])) if float(data['price']) >= 0 else 0,
            stock=0 if has_sizes else int(data['stock']),
            category_id=int(data['category_id']),
            sku=data['sku'],
            is_active=bool(int(data.get('is_active', 0))),
            has_sizes=has_sizes
        )
        
        db.session.add(product)
        db.session.flush()

        try:
            handle_product_images(product, request.files)
            
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
                product.stock = total_stock
            
            db.session.commit()
            flash('Product created successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
        except Exception as e:
            db.session.rollback()
            flash('Error creating product', 'error')
    
    categories = Category.query.all()
    return render_template('admin/product_form.html', categories=categories)

@admin_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.options(db.joinedload(Product.images)).get_or_404(id)
    
    if request.method == 'POST':
        try:
            data = request.form
            category = Category.query.get(int(data['category_id']))
            has_sizes = category.has_sizes if category else False

            product.name = data['name']
            product.description = data['description']
            product.price = int(float(data['price'])) if float(data['price']) >= 0 else product.price
            product.category_id = int(data['category_id'])
            product.sku = data['sku']
            product.is_active = bool(int(data.get('is_active', 0)))
            product.has_sizes = has_sizes

            if not has_sizes and not data.getlist('color_names[]'):
                product.stock = int(data.get('stock', 0))

            # Handle images
            images_to_keep = request.form.getlist('existing_images')
            for image in product.images[:]:
                if str(image.id) not in images_to_keep:
                    delete_product_image(image)
            
            handle_product_images(product, request.files)

            # Handle sizes if applicable
            if has_sizes:
                for size in product.sizes[:]:
                    db.session.delete(size)
                
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
                product.stock = total_stock

            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error updating product', 'error')
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

@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        for image in product.images:
            delete_product_image(image)
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully!', 'success')
    except:
        db.session.rollback()
        flash('Error deleting product', 'error')
    return redirect(url_for('admin.manage_products'))

@admin_bp.route('/products/<int:id>/images/<int:image_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_image(id, image_id):
    image = ProductImage.query.get_or_404(image_id)
    if image.product_id != id:
        abort(404)
    try:
        delete_product_image(image)
        db.session.commit()
        return jsonify({'success': True})
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete image'}), 500

@admin_bp.route('/products/<int:id>/images/<int:image_id>/make-primary', methods=['POST'])
@login_required
@admin_required
def make_image_primary(id, image_id):
    image = ProductImage.query.get_or_404(image_id)
    if image.product_id != id:
        abort(404)
    try:
        # Set all other images as non-primary
        for img in image.product.images:
            img.is_primary = (img.id == image_id)
        db.session.commit()
        return jsonify({'success': True})
    except:
        db.session.rollback()
        return jsonify({'error': 'Failed to update primary image'}), 500