from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, session
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, validators
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from models import User, Order
from functools import wraps
import os
import re
import logging
from extensions import db, init_oauth

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Create blueprint
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

@auth_bp.route('/login/google')
def google_login():
    """Initiate Google OAuth login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    # Store next URL in session
    next_url = request.args.get('next')
    if next_url:
        session['next'] = next_url

    # Get OAuth instance
    oauth = current_app.extensions.get('authlib.integrations.flask_client')
    if not oauth:
        flash('OAuth configuration error', 'error')
        return redirect(url_for('auth.login'))

    google = oauth.create_client('google')
    return google.authorize_redirect()

@auth_bp.route('/google/google/authorized')
def google_callback():
    """Handle the Google OAuth callback"""
    try:
        oauth = current_app.extensions.get('authlib.integrations.flask_client')
        google = oauth.create_client('google')
        
        # Get token and user info
        token = google.authorize_access_token()
        resp = google.get('https://openidconnect.googleapis.com/v1/userinfo')
        user_info = resp.json()
        
        email = user_info.get('email')
        if not email:
            flash('Failed to get email from Google.', 'error')
            return redirect(url_for('auth.login'))

        # Check if user exists
        user = User.query.filter_by(email=email, provider='google').first()
        if not user:
            # Check if email exists but with different provider
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                existing_user.provider = 'google'
                existing_user.oauth_token = token
                db.session.commit()
                login_user(existing_user)
                return redirect(url_for('main.home'))

            # Create new user
            username = email.split('@')[0]
            base_username = username
            counter = 1
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1

            user = User(
                email=email,
                username=username,
                first_name=user_info.get('given_name', ''),
                last_name=user_info.get('family_name', ''),
                password=os.urandom(24).hex(),
                provider='google',
                oauth_token=token,
                profile_picture=user_info.get('picture')
            )
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully!', 'success')

        # Log the user in
        login_user(user)
        next_page = session.pop('next', url_for('main.home'))
        return redirect(next_page)

    except Exception as e:
        logger.error(f"Google OAuth error: {str(e)}")
        logger.exception(e)
        flash('Failed to authenticate with Google. Please try again.', 'error')
        return redirect(url_for('auth.login'))

@auth_bp.route('/profile')
@login_required
def profile():
    """User profile page"""
    return render_template('auth/profile.html', user=current_user)

class ProfileEditForm(FlaskForm):
    first_name = StringField('First Name')
    last_name = StringField('Last Name')
    phone_number = StringField('Phone Number')
    address_line1 = StringField('Address Line 1')
    address_line2 = StringField('Address Line 2')
    city = StringField('City')
    state = StringField('State')
    postal_code = StringField('Postal Code')
    current_password = PasswordField('Current Password')
    new_password = PasswordField('New Password', [
        validators.Optional(),
        validators.Length(min=8, message='Password must be at least 8 characters long')
    ])
    confirm_password = PasswordField('Confirm New Password', [
        validators.EqualTo('new_password', message='Passwords must match')
    ])

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """Edit user profile"""
    form = ProfileEditForm()
    
    if form.validate_on_submit():
        try:
            # Update password if provided
            if form.new_password.data:
                if not form.current_password.data:
                    flash('Current password is required to change password', 'error')
                    return redirect(url_for('auth.edit_profile'))
                
                if not current_user.verify_password(form.current_password.data):
                    flash('Current password is incorrect', 'error')
                    return redirect(url_for('auth.edit_profile'))
                
                current_user.password = form.new_password.data

            # Update user information
            current_user.first_name = form.first_name.data
            current_user.last_name = form.last_name.data
            current_user.phone_number = form.phone_number.data
            current_user.address_line1 = form.address_line1.data
            current_user.address_line2 = form.address_line2.data
            current_user.city = form.city.data
            current_user.state = form.state.data
            current_user.postal_code = form.postal_code.data

            # Save changes
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('auth.profile'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Profile update error: {str(e)}")
            flash('An error occurred while updating your profile', 'error')
            return redirect(url_for('auth.edit_profile'))

    # Pre-fill form with current user data
    if request.method == 'GET':
        form.first_name.data = current_user.first_name
        form.last_name.data = current_user.last_name
        form.phone_number.data = current_user.phone_number
        form.address_line1.data = current_user.address_line1
        form.address_line2.data = current_user.address_line2
        form.city.data = current_user.city
        form.state.data = current_user.state
        form.postal_code.data = current_user.postal_code

    return render_template('auth/edit_profile.html', form=form, user=current_user)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle user registration"""
    if request.method == 'POST':
        email = request.form.get('email')
        username = request.form.get('username')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
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
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('auth.register'))
            
        if User.query.filter_by(username=username).first():
            flash('Username already taken', 'error')
            return redirect(url_for('auth.register'))
        
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            password=password
        )
        
        try:
            db.session.add(user)
            db.session.commit()
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            db.session.rollback()
            flash('An error occurred during registration', 'error')
            return redirect(url_for('auth.register'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user login"""
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))

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
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('main.home'))
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """Handle user logout"""
    logout_user()
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('main.home'))
@auth_bp.route('/purchase-history')
@login_required
def purchase_history():
    """Display user's purchase history"""
    page = request.args.get('page', 1, type=int)
    per_page = 10  # Number of orders per page
    
    # Query orders for current user with pagination
    orders = db.session.query(Order)\
        .filter_by(user_id=current_user.id)\
        .order_by(Order.created_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)
        
    return render_template('auth/purchase_history.html', orders=orders)

# Enable OAuth for development
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
