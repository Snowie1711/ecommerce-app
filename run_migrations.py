from flask import Flask
from flask_migrate import Migrate
from extensions import db
from models.order import Order  # Import models to register with SQLAlchemy
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    db.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    migrate = Migrate(app, db)
    
    with app.app_context():
        from flask_migrate import upgrade
        # Upgrade to our specific migration
        upgrade('9a7b6c5d4e3f')
        print("Database migration completed successfully!")
