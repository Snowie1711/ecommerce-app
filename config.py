import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Debug environment variables
print("\n🔍 Debugging Environment Variables:")
print(f"PAYOS_CLIENT_ID: {os.environ.get('PAYOS_CLIENT_ID', 'Not set')}")
print(f"PAYOS_API_KEY: {os.environ.get('PAYOS_API_KEY', 'Not set')}")
print(f"PAYOS_SECRET_KEY: {os.environ.get('PAYOS_SECRET_KEY', 'Not set')}\n")

class Config:
    # Secret key for session management and security
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key'
    
    # Base URL for callbacks
    BASE_URL = os.environ.get('BASE_URL', 'http://localhost:5000')
    
    # PayOS configuration
    PAYOS_CLIENT_ID = os.environ.get('PAYOS_CLIENT_ID')
    PAYOS_API_KEY = os.environ.get('PAYOS_API_KEY')
    PAYOS_SECRET_KEY = os.environ.get('PAYOS_SECRET_KEY')
    
    # Database configuration
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///ecommerce.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # JWT configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY') or 'jwt-secret-key'
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    
    # Upload configuration
    UPLOAD_FOLDER = os.path.join('static', 'uploads')  # Relative to app root
    UPLOADS_DEFAULT_DEST = os.path.join('static', 'uploads')  # For Flask-Uploads
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    # Mail configuration (for password reset)
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    
    # Pagination
    PRODUCTS_PER_PAGE = 12
    ORDERS_PER_PAGE = 10

class DevelopmentConfig(Config):
    DEBUG = True
    
    # OAuth settings
    OAUTHLIB_INSECURE_TRANSPORT = True
    OAUTHLIB_RELAX_TOKEN_SCOPE = True
    OAUTHLIB_DEBUG = True
    
    # Server settings
    SERVER_NAME = "127.0.0.1:5000"
    PREFERRED_URL_SCHEME = "http"
    
    # Debug settings
    EXPLAIN_TEMPLATE_LOADING = True
    TRAP_HTTP_EXCEPTIONS = True
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Enable OAuth on http
    
class ProductionConfig(Config):
    DEBUG = False
    # In production, ensure to set proper secret keys through environment variables
    
class TestingConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///test.db'
    WTF_CSRF_ENABLED = False

# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}