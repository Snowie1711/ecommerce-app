from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Order
from functools import wraps
import re

auth_bp = Blueprint('auth', __name__)

def admin_required(f):
    """Decorator to check if current user is admin"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('You need administrator privileges to access this page.', 'error')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        # Basic validation
        if not email or not password or not username:
            flash('Email, username, and password are required', 'error')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return redirect(url_for('auth.register'))
            
        if len(password) < 8:
            flash('Password must be at least 8 characters long', 'error')
            return redirect(url_for('auth.register'))
            
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email address', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password  # Password will be hashed by User model
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            current_app.logger.error(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during registration', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(email=email).first()
        
        if not user or not user.verify_password(password):
            flash('Invalid email or password', 'error')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        
        # Redirect to next page if specified
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
            
        return redirect(url_for('main.home'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        # Update user information
        current_user.first_name = request.form.get('first_name', '')
        current_user.last_name = request.form.get('last_name', '')
        current_user.address_line1 = request.form.get('address_line1', '')
        current_user.address_line2 = request.form.get('address_line2', '')
        current_user.city = request.form.get('city', '')
        current_user.state = request.form.get('state', '')
        current_user.postal_code = request.form.get('postal_code', '')
        current_user.phone_number = request.form.get('phone_number', '')
        
        # Update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            current_password = request.form.get('current_password')
            if not current_user.verify_password(current_password):
                flash('Current password is incorrect', 'error')
                return redirect(url_for('auth.profile'))
            
            if len(new_password) < 8:
                flash('New password must be at least 8 characters long', 'error')
                return redirect(url_for('auth.profile'))
                
            current_user.password = new_password  # Will be hashed by User model
        
        try:
            db.session.commit()
            flash('Profile updated successfully', 'success')
        except Exception as e:
            current_app.logger.error(f"Profile update error: {str(e)}")
            db.session.rollback()
            flash('An error occurred while updating your profile', 'error')
        
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/profile.html')

@auth_bp.route('/payment-methods', methods=['GET', 'POST'])
@login_required
def payment_methods():
    if request.method == 'POST':
        payment_provider = request.form.get('payment_provider')
        payment_token = request.form.get('payment_token')
        
        if not payment_provider or not payment_token:
            flash('Payment provider and token are required', 'error')
            return redirect(url_for('auth.payment_methods'))
        
        # Validate payment provider
        if payment_provider not in ['credit_card', 'payos', 'cod']:
            current_app.logger.error(f'Invalid payment provider: {payment_provider}')
            flash('Invalid payment provider', 'error')
            return redirect(url_for('auth.payment_methods'))
        
        try:
            current_user.payment_provider = payment_provider
            current_user.payment_method_id = payment_token
            db.session.commit()
            flash('Payment method updated successfully', 'success')
        except Exception as e:
            current_app.logger.error(f"Payment method update error: {str(e)}")
            db.session.rollback()
            flash('Failed to update payment method', 'error')
        
        return redirect(url_for('auth.payment_methods'))
    
    return render_template('auth/payment_methods.html')

@auth_bp.route('/purchase-history')
@login_required
def purchase_history():
    page = request.args.get('page', 1, type=int)
    orders = Order.query.filter_by(user_id=current_user.id)\
                       .order_by(Order.created_at.desc())\
                       .paginate(page=page, per_page=10)
    return render_template('auth/purchase_history.html', orders=orders)