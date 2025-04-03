from flask import Flask, render_template
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from models import db, User
from config import config
import os

login_manager = LoginManager()
csrf = CSRFProtect()

def create_app(config_name='default'):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])
    
    # Ensure the upload folder exists and has correct permissions
    upload_folder = os.path.join(app.root_path, app.config['UPLOAD_FOLDER'])
    if not os.path.exists(upload_folder):
        os.makedirs(upload_folder, mode=0o755, exist_ok=True)
    
    # Update config to use absolute path
    app.config['UPLOAD_FOLDER'] = upload_folder
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    Migrate(app, db)
    
    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Configure login settings
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.products import products_bp
    from routes.cart import cart_bp
    from routes.admin import admin_bp
    from routes.api import api_bp
    from routes.main import bp as main_bp
    from routes.payment import payment
    from routes.orders import orders
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(products_bp)
    app.register_blueprint(cart_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(payment, url_prefix='/payment')
    app.register_blueprint(orders, url_prefix='/orders')
    
    # Context processors
    @app.context_processor
    def utility_processor():
        from datetime import datetime
        return {
            'current_year': datetime.utcnow().year,
            'min': min
        }

    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        if app.debug:
            return str(error), 404
        return render_template('errors/error.html', error='Not Found'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if app.debug:
            import traceback
            return f"<pre>{traceback.format_exc()}</pre>", 500
        return render_template('errors/error.html', error='Internal Server Error'), 500
    
    # Create database tables if they don't exist
    with app.app_context():
        db.create_all()
    
    return app

if __name__ == '__main__':
    app = create_app('development')
    app.run(debug=True)