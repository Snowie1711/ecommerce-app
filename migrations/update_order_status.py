"""
Migration script to update order statuses from PENDING to PAID
"""
import sqlite3
import os

def update_order_statuses():
    """
    Update existing orders with PENDING status to PAID using direct SQLite connection
    This avoids SQLAlchemy's enum validation during the migration
    """
    try:
        # Get the absolute path to the database file
        db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'instance', 'ecommerce.db')
        
        # Connect directly to SQLite database
        print(f"Connecting to database at: {db_path}")
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Update orders with PENDING status to PAID
        cursor.execute("UPDATE orders SET status = 'PAID' WHERE status = 'PENDING'")
        updated_rows = cursor.rowcount
        
        # Commit the changes
        conn.commit()
        
        print(f"Successfully updated {updated_rows} orders from PENDING to PAID")
        
        # Close the connection
        conn.close()
        
    except Exception as e:
        print(f"Error updating order statuses: {str(e)}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()

if __name__ == '__main__':
    update_order_statuses()