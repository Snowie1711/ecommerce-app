from app import create_app
from extensions import db
from sqlalchemy import text
import shutil
import os

def cleanup_database():
    """Clean up temporary tables and migrations"""
    app = create_app()
    
    with app.app_context():
        conn = db.engine.connect()
        try:
            # List of temporary tables to drop
            temp_tables = [
                '_alembic_tmp_notifications',
                '_alembic_tmp_product_colors',
                '_alembic_tmp_product_sizes',
                '_alembic_tmp_product_variant',
                'product_variant',
                'product_colors',
                'product_sizes',
                'alembic_version'
            ]
            
            # Drop each table if it exists
            for table in temp_tables:
                try:
                    conn.execute(text(f'DROP TABLE IF EXISTS {table}'))
                    print(f"Dropped table {table} if it existed")
                except Exception as e:
                    print(f"Error dropping {table}: {str(e)}")
            
            # Commit the changes
            conn.commit()
            print("Database cleanup completed successfully")
            
        except Exception as e:
            print(f"Error during database cleanup: {str(e)}")
        finally:
            conn.close()

    # Remove migrations folder
    migrations_path = os.path.join(os.path.dirname(__file__), 'migrations')
    if os.path.exists(migrations_path):
        try:
            shutil.rmtree(migrations_path)
            print("Removed migrations folder successfully")
        except Exception as e:
            print(f"Error removing migrations folder: {str(e)}")

if __name__ == "__main__":
    cleanup_database()
