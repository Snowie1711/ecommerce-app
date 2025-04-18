from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_migrate import Migrate
from authlib.integrations.flask_client import OAuth
from flask_socketio import SocketIO

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
csrf = CSRFProtect()

# Initialize SocketIO without specifying async_mode yet
# We'll set it dynamically in run.py
socketio = SocketIO(cors_allowed_origins="*")

def init_oauth(app):
    oauth = OAuth(app)
    oauth.register(
        name='google',
        client_id=app.config.get('GOOGLE_CLIENT_ID'),
        client_secret=app.config.get('GOOGLE_CLIENT_SECRET'),
        server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
        userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo',
        client_kwargs={
            'scope': 'openid email profile',
            'redirect_uri': 'http://127.0.0.1:5000/auth/google/google/authorized'
        }
    )
    return oauth