from flask import Flask
import logging
import os
from config import config
from extensions import db, migrate, login_manager, csrf, init_oauth, socketio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Configure Google OAuth and secret key
    app.config["GOOGLE_CLIENT_ID"] = os.getenv("GOOGLE_CLIENT_ID")
    app.config["GOOGLE_CLIENT_SECRET"] = os.getenv("GOOGLE_CLIENT_SECRET")
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", os.urandom(24))
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    socketio.init_app(app, cors_allowed_origins="*")
    
    # Initialize OAuth
    oauth = init_oauth(app)
    
    with app.app_context():
        # Import models
        from models import User, Product, Order, OrderItem, OrderStatus, Category, ProductImage, Review
        
        # Set up login configuration
        login_manager.login_view = 'auth.login'
        login_manager.login_message_category = 'info'
        
        @login_manager.user_loader
        def load_user(user_id):
            return User.query.get(int(user_id))
    
    # Configure logging
    if not app.debug:
        file_handler = logging.FileHandler('app.log')
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)
    
    # Set up debug logging
    if app.debug:
        logging.basicConfig(level=logging.DEBUG)
        logger = logging.getLogger('flask_dance')
        logger.addHandler(logging.StreamHandler())
        logger.setLevel(logging.DEBUG)
    
    # Register blueprints
    from routes.main import main_bp
    from routes.auth import auth_bp
    from routes.products import products_bp
    from routes.cart import cart_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes.orders import orders_bp
    from routes.payment import payment_bp
    from routes.reviews import reviews_bp
    from routes import websocket  # Import websocket routes
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(orders_bp, url_prefix='/orders')
    app.register_blueprint(payment_bp, url_prefix='/payment')
    app.register_blueprint(reviews_bp)

    # Template filters
    @app.template_filter('format_number')
    def format_number(value):
        """Format large numbers with commas as thousands separators"""
        try:
            return "{:,.0f}".format(value)
        except (ValueError, TypeError):
            return "0"
            
    @app.template_filter('get_size_stock')
    def get_size_stock(size, product):
        """Get stock for a specific size of a product"""
        if not size or not product:
            return 0
        size_obj = next((s for s in product.sizes if s.size == size), None)
        return size_obj.stock if size_obj else 0
        
    @app.template_filter('get_size_stock_by_sizes')
    def get_size_stock_by_sizes(sizes, size):
        """Get stock for a specific size from a sizes list"""
        if not sizes or not size:
            return 0
        size_obj = next((s for s in sizes if s.size == size), None)
        return size_obj.stock if size_obj else 0
    
    # Error handlers
    from error_handlers import init_error_handlers, ValidationError, handle_validation_error
    init_error_handlers(app)
    app.register_error_handler(ValidationError, handle_validation_error)
    
    return app

def run_app(app):
    """Run the application with SocketIO support"""
    socketio.run(app, debug=app.debug, allow_unsafe_werkzeug=True)

if __name__ == '__main__':
    app = create_app()
    run_app(app)
