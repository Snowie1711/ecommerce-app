"""
Database Check and Update Script

This script checks if the shipping_fee column exists in the orders table
and adds it if needed.
"""

import os
import sys
import sqlite3
from flask import Flask
from app import create_app
from migrations.add_shipping_fee import upgrade as add_shipping_fee

def check_and_update_db():
    """Check and update the database schema if needed"""
    app = create_app()
    
    with app.app_context():
        # Get database path from app config
        db_uri = app.config['SQLALCHEMY_DATABASE_URI']
        
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.replace('sqlite:///', '')
            
            # Make path absolute if it's relative
            if not os.path.isabs(db_path):
                db_path = os.path.join(os.path.dirname(__file__), db_path)
            
            print(f"Checking database schema in {db_path}")
            
            try:
                # Connect to the database
                conn = sqlite3.connect(db_path)
                cursor = conn.cursor()
                
                # Check if shipping_fee column exists
                cursor.execute("PRAGMA table_info(orders)")
                columns = [column[1] for column in cursor.fetchall()]
                
                if 'shipping_fee' not in columns:
                    print("❌ shipping_fee column is missing in orders table")
                    print("Running migration to add the column...")
                    add_shipping_fee()
                    print("✅ Migration completed successfully!")
                else:
                    print("✅ Database schema is up to date")
                
                conn.close()
                return 0
            except Exception as e:
                print(f"❌ Error checking database schema: {str(e)}")
                return 1
        else:
            print(f"⚠️ Non-SQLite database detected: {db_uri}")
            print("  Please run migrations using the appropriate database tools")
            return 0

if __name__ == "__main__":
    sys.exit(check_and_update_db())
