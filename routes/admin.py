from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, current_app, abort
from flask_login import login_required
from extensions import db
from models import User, Product, Order, OrderItem, Category, OrderStatus, ProductImage, ProductSize, ProductColor, ProductVariant, Notification
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
        if (first_image):
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

@admin_bp.route('/orders/<int:order_id>/reject-cancellation', methods=['POST'])
@login_required
@admin_required
def reject_cancellation(order_id):
    """Handle rejection of cancellation requests via AJAX."""
    order = Order.query.get_or_404(order_id)
    
    if not order.cancellation_requested:
        return jsonify({'error': 'This order has no cancellation request.'}), 400
    
    try:
        order.cancellation_requested = False
        order.cancellation_approved = False
        
        # Create notification for the user
        notification = Notification(
            user_id=order.user_id,
            message=f"Your cancellation request for Order #{order.id} has been rejected",
            link=url_for('orders.order_detail', order_id=order.id)
        )
        db.session.add(notification)
        db.session.commit()
        
        return jsonify({'success': True}), 200
    except:
        db.session.rollback()
        return jsonify({'error': 'Error processing cancellation request.'}), 500


@admin_bp.route('/orders/cancellation-requests')
@login_required
@admin_required
def cancellation_requests():
    """Display list of orders with cancellation requests."""
    orders = Order.query.filter(
        Order.cancellation_requested == True,
        Order.status.in_([OrderStatus.PENDING_PAYMENT, OrderStatus.PROCESSING, OrderStatus.PAID])
    ).order_by(Order.created_at.desc()).all()
    
    return render_template('admin/cancellation_requests.html', orders=orders)

@admin_bp.route('/orders/<int:order_id>/handle-cancellation', methods=['POST'])
@login_required
@admin_required
def handle_cancellation(order_id):
    """Handle approval or rejection of cancellation requests."""
    order = Order.query.get_or_404(order_id)
    action = request.form.get('action')
    
    if not order.cancellation_requested:
        flash('This order has no cancellation request.', 'error')
        return redirect(url_for('admin.cancellation_requests'))
    
    notification_message = ""
    if action == 'approve':
        order.status = OrderStatus.CANCELLED
        order.cancellation_approved = True
        notification_message = f"Your cancellation request for Order #{order.id} has been approved"
        flash('Cancellation request approved.', 'success')
    elif action == 'reject':
        order.cancellation_approved = False
        notification_message = f"Your cancellation request for Order #{order.id} has been rejected"
        flash('Cancellation request rejected.', 'warning')
    else:
        flash('Invalid action.', 'error')
        return redirect(url_for('admin.cancellation_requests'))
    
    try:
        # Create notification for the user
        notification = Notification(
            user_id=order.user_id,
            message=notification_message,
            link=url_for('orders.order_detail', order_id=order.id)
        )
        db.session.add(notification)
        db.session.commit()
    except:
        db.session.rollback()
        flash('Error processing cancellation request.', 'error')
    
    return redirect(url_for('admin.cancellation_requests'))

@admin_bp.route('/')
@login_required
@admin_required
def dashboard():
    # Get summary statistics
    total_users = User.query.count()
    total_products = Product.query.count()
    total_orders = Order.query.count()
    
    # Calculate total revenue
    revenue = db.session.query(func.sum(Order.total_amount)).filter(Order.status != OrderStatus.CANCELLED).scalar() or 0
    
    # Get recent orders
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(5).all()
    
    # Get low stock regular products (less than 10 items)
    low_stock = Product.query.filter(
        Product.inventory_type == 'regular',
        Product.stock < 10
    ).all()
    
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
        new_status = OrderStatus.from_string(status)
        old_status = order.status
        
        # Check if status is changing to DELIVERED
        if new_status == OrderStatus.DELIVERED and old_status != OrderStatus.DELIVERED:
            # Reduce stock for each item
            for item in order.items:
                product = item.product
                if product.inventory_type == 'regular':
                    if product.stock >= item.quantity:
                        product.stock -= item.quantity
                        current_app.logger.info(f"Reduced stock for product {product.id} by {item.quantity}")
                    else:
                        product.stock = 0
                        current_app.logger.warning(f"Product {product.id} stock reduced to 0 (requested: {item.quantity}, available: {product.stock})")
                elif product.inventory_type == 'size':
                    variant = ProductSize.query.get(item.size_id)
                    if variant:
                        if variant.stock >= item.quantity:
                            variant.stock -= item.quantity
                            current_app.logger.info(f"Reduced stock for product {product.id} size {variant.name} by {item.quantity}")
                        else:
                            variant.stock = 0
                            current_app.logger.warning(f"Product {product.id} size {variant.name} stock reduced to 0")
                elif product.inventory_type == 'color':
                    variant = ProductColor.query.get(item.color_id)
                    if variant:
                        if variant.stock >= item.quantity:
                            variant.stock -= item.quantity
                            current_app.logger.info(f"Reduced stock for product {product.id} color {variant.name} by {item.quantity}")
                        else:
                            variant.stock = 0
                            current_app.logger.warning(f"Product {product.id} color {variant.name} stock reduced to 0")
                elif product.inventory_type == 'both':
                    variant = ProductVariant.query.filter_by(
                        product_id=product.id,
                        size_id=item.size_id,
                        color_id=item.color_id
                    ).first()
                    if variant:
                        if variant.stock >= item.quantity:
                            variant.stock -= item.quantity
                            current_app.logger.info(f"Reduced stock for product {product.id} variant (size: {item.size_id}, color: {item.color_id}) by {item.quantity}")
                        else:
                            variant.stock = 0
                            current_app.logger.warning(f"Product {product.id} variant stock reduced to 0")

        order.status = new_status
        
        if status.lower() == OrderStatus.SHIPPED.value:
            order.tracking_number = request.form.get('tracking_number')
        
        # Create notification for status change
        notification_message = f"Order #{order.id} has been updated to {new_status.value}"
        if new_status == OrderStatus.SHIPPED:
            tracking = order.tracking_number
            if tracking:
                notification_message += f" (Tracking: {tracking})"
                
        notification = Notification(
            user_id=order.user_id,
            message=notification_message,
            link=url_for('orders.order_detail', order_id=order.id)
        )
        db.session.add(notification)
        
        try:
            db.session.commit()
            flash('Order status updated successfully!', 'success')
        except:
            db.session.rollback()
            flash('Error updating order status', 'error')
    except ValueError:
        flash('Invalid status', 'error')
    
    return redirect(url_for('admin.order_detail', id=id))


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
        
    # Apply sorting
    if sort == 'name':
        query = query.order_by(Product.name)
    elif sort == 'price':
        query = query.order_by(Product.price)
    elif sort == 'stock':
        query = query.order_by(Product.stock)
    elif sort == 'category':
        query = query.order_by(Category.name)

    # Paginate results
    products = query.paginate(
        page=page,
        per_page=current_app.config['PRODUCTS_PER_PAGE'],
        error_out=False
    )
    
    # Get categories for filter dropdown
    categories = Category.query.order_by(Category.name).all()
    
    return render_template('admin/products.html',
                       products=products,
                       categories=categories,
                       selected_category=category,
                       sort=sort,
                       search=search)

@admin_bp.route('/products/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_product():
    if request.method == 'POST':
        try:
            # Get basic product info
            name = request.form.get('name')
            description = request.form.get('description')
            price = int(float(request.form.get('price', 0)) * 1000)  # Convert to VND
            stock = int(request.form.get('stock', 0))
            category_id = request.form.get('category_id')
            inventory_type = request.form.get('inventory_type', 'regular')
            has_sizes = request.form.get('has_sizes') == 'true'
            
            # Create new product
            product = Product(
                name=name,
                description=description,
                price=price,
                stock=stock,
                category_id=category_id,
                inventory_type=inventory_type,
                has_sizes=has_sizes
            )
            db.session.add(product)
            db.session.commit()  # Commit first to get product.id
            
            # Handle images after commit
            if 'images' in request.files:
                handle_product_images(product, request.files)
                db.session.commit()  # Commit the image changes
            flash('Product created successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            db.session.rollback()
            flash('Error creating product: ' + str(e), 'error')
            
    return render_template('admin/product_form.html',
                         product=None,
                         categories=Category.query.all(),
                         inventory_types=['regular', 'size', 'color', 'both'])

@admin_bp.route('/products/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_product(id):
    product = Product.query.get_or_404(id)
    if request.method == 'POST':
        try:
            # Update basic product info
            product.name = request.form.get('name')
            product.description = request.form.get('description')
            product.price = int(float(request.form.get('price', 0)) * 1000)  # Convert to VND
            product.category_id = request.form.get('category_id')
            product.inventory_type = request.form.get('inventory_type', 'regular')
            product.has_sizes = request.form.get('has_sizes') == 'true'

            # Handle inventory based on type
            if product.inventory_type == 'regular':
                # For regular products, directly set the stock value
                # Fix: Use 'regular_stock' instead of 'stock' to match the form field name
                stock_value = request.form.get('regular_stock', '0')
                product.stock = int(stock_value)
                current_app.logger.info(f"Set regular inventory stock to: {product.stock}")

            elif product.inventory_type == 'size':
                product.sizes.clear()
                sizes = request.form.getlist('sizes[]')
                size_stocks = request.form.getlist('size_stocks[]')

                # Add each size with its stock
                for size, stock in zip(sizes, size_stocks):
                    if size:
                        stock_int = int(stock or 0)
                        size_obj = ProductSize(
                            product_id=product.id,
                            size=size,
                            stock=stock_int
                        )
                        product.sizes.append(size_obj)
                
                # Flush to ensure all sizes are added before calculating total
                db.session.flush()
                
                # Calculate total stock from sizes
                total_stock = sum(size.stock for size in product.sizes)
                product.stock = total_stock
                current_app.logger.info(f"Updated size inventory - total stock: {total_stock}")

            elif product.inventory_type == 'color':
                product.colors.clear()
                color_names = request.form.getlist('color_names[]')
                color_codes = request.form.getlist('color_codes[]')
                color_stocks = request.form.getlist('color_stocks[]')

                total_stock = 0
                for name, code, stock in zip(color_names, color_codes, color_stocks):
                    if name and code:
                        stock_int = int(stock or 0)
                        color = ProductColor(
                            product_id=product.id,
                            color_name=name,
                            color_code=code,
                            stock=stock_int
                        )
                        product.colors.append(color)
                        total_stock += stock_int
                product.stock = total_stock
                current_app.logger.info(f"Updated color inventory - total stock: {total_stock}")

            elif product.inventory_type == 'both':
                product.variants.clear()
                variant_sizes = request.form.getlist('variant_sizes[]')
                variant_colors = request.form.getlist('variant_colors[]')
                variant_codes = request.form.getlist('variant_codes[]')
                variant_stocks = request.form.getlist('variant_stocks[]')

                # First flush the session to get IDs for new sizes and colors
                db.session.flush()

                size_map = {}
                color_map = {}

                for size in set(variant_sizes):
                    if size:
                        size_obj = ProductSize(product_id=product.id, size=size, stock=0)
                        db.session.add(size_obj)
                        size_map[size] = size_obj

                for color_name, color_code in set(zip(variant_colors, variant_codes)):
                    if color_name and color_code:
                        color_obj = ProductColor(product_id=product.id, color_name=color_name, color_code=color_code, stock=0)
                        db.session.add(color_obj)
                        color_map[color_name] = color_obj

                # Flush again to get IDs for new sizes and colors
                db.session.flush()

                total_stock = 0
                for size, color_name, color_code, stock in zip(variant_sizes, variant_colors, variant_codes, variant_stocks):
                    if size and color_name:
                        size_obj = size_map[size]
                        color_obj = color_map[color_name]
                        stock_int = int(stock or 0)
                        variant = ProductVariant(
                            product_id=product.id,
                            size_id=size_obj.id,
                            color_id=color_obj.id,
                            stock=stock_int
                        )
                        product.variants.append(variant)
                        total_stock += stock_int
                product.stock = total_stock
                current_app.logger.info(f"Updated variant inventory - total stock: {total_stock}")
            
            # Handle images
            if 'images' in request.files:
                handle_product_images(product, request.files,
                                   existing_primary=request.form.get('primary_image'))
            
            # Ensure all changes are flushed to the database
            db.session.flush()
            
            # Final stock recalculation for all inventory types
            if product.inventory_type == 'regular':
                # For regular products, the stock was directly set above
                current_app.logger.info(f"Final regular stock: {product.stock}")
            else:
                # For variant products, double-check the stock calculation
                old_stock = product.stock
                new_stock = product.recalculate_stock()
                current_app.logger.info(f"Recalculated stock: {old_stock} -> {new_stock}")
            
            # Cập nhật in_stock cuối cùng (cho cả regular, size, color, both)
            # Only update from in_stock if the field is present in the form
            if 'in_stock' in request.form:
                product.stock = int(request.form.get('in_stock', 0))
                current_app.logger.info(f"Set final product.stock from form in_stock = {product.stock}")
            # If in_stock is not provided but this is a regular product, ensure we use the regular_stock value
            elif product.inventory_type == 'regular':
                # This ensures the regular_stock value is respected as the final value
                product.stock = int(request.form.get('regular_stock', 0))
                current_app.logger.info(f"Set final product.stock from regular_stock = {product.stock}")
            
            # Commit all changes
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('admin.manage_products'))
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f"Error updating product: {str(e)}")
            current_app.logger.exception("Stack trace:")
            flash('Error updating product: ' + str(e), 'error')
    return render_template('admin/product_form.html', product=product, categories=Category.query.all())

@admin_bp.route('/products/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_product(id):
    product = Product.query.get_or_404(id)
    try:
        db.session.delete(product)
        db.session.commit()
        flash('Product deleted successfully', 'success')
    except:
        db.session.rollback()
        flash('Error deleting product', 'error')
    return redirect(url_for('admin.manage_products'))