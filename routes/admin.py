from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required
from models import db, User, Product, Order, OrderItem, Category, OrderStatus
from routes.auth import admin_required
from sqlalchemy import func
from datetime import datetime, timedelta
import json

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/admin/')
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

@admin_bp.route('/admin/users')
@login_required
@admin_required
def manage_users():
    page = request.args.get('page', 1, type=int)
    users = User.query.paginate(page=page, per_page=20)
    return render_template('admin/users.html', users=users)

@admin_bp.route('/admin/users/<int:id>/toggle-status', methods=['POST'])
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

@admin_bp.route('/admin/analytics')
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
        'revenue': [float(row.revenue) for row in sales_data]
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

@admin_bp.route('/admin/orders')
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

@admin_bp.route('/admin/orders/<int:id>')
@login_required
@admin_required
def order_detail(id):
    order = Order.query.get_or_404(id)
    return render_template('admin/order_detail.html', order=order, statuses=OrderStatus)

@admin_bp.route('/admin/orders/<int:id>/update-status', methods=['POST'])
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

# API endpoints
@admin_bp.route('/api/admin/stats')
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
        'total_revenue': float(revenue)
    })

@admin_bp.route('/api/admin/sales-data')
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

@admin_bp.route('/admin/users/<int:id>/update-password', methods=['POST'])
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