from app import create_app
from extensions import db
from models import Product, ProductSize, ProductColor, ProductVariant
from sqlalchemy import text

def create_product_tables():
    """Create the product variant tables directly without migrations"""
    app = create_app()
    
    with app.app_context():
        conn = db.engine.connect()
        try:
            # First check if tables exist
            table_exists_query = text("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('product_sizes', 'product_colors', 'product_variant')
            """)
            existing_tables = [row[0] for row in conn.execute(table_exists_query)]
            
            # Create product_sizes table if it doesn't exist
            if 'product_sizes' not in existing_tables:
                print("Creating product_sizes table...")
                conn.execute(text("""
                    CREATE TABLE product_sizes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        size VARCHAR(20) NOT NULL,
                        stock INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                    )
                """))
                print("Created product_sizes table")
            else:
                print("product_sizes table already exists")

            # Create product_colors table if it doesn't exist
            if 'product_colors' not in existing_tables:
                print("Creating product_colors table...")
                conn.execute(text("""
                    CREATE TABLE product_colors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        color_name VARCHAR(50) NOT NULL,
                        color_code VARCHAR(20),
                        stock INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE
                    )
                """))
                print("Created product_colors table")
            else:
                print("product_colors table already exists")

            # Create product_variant table if it doesn't exist
            if 'product_variant' not in existing_tables:
                print("Creating product_variant table...")
                conn.execute(text("""
                    CREATE TABLE product_variant (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        product_id INTEGER NOT NULL,
                        size_id INTEGER NOT NULL,
                        color_id INTEGER NOT NULL,
                        stock INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY (product_id) REFERENCES products (id) ON DELETE CASCADE,
                        FOREIGN KEY (size_id) REFERENCES product_sizes (id) ON DELETE CASCADE,
                        FOREIGN KEY (color_id) REFERENCES product_colors (id) ON DELETE CASCADE
                    )
                """))
                print("Created product_variant table")
            else:
                print("product_variant table already exists")
            
            # Also update cart_items table to add variant_id if needed
            cart_items_query = text("""
                SELECT sql FROM sqlite_master
                WHERE type='table' AND name='cart_items'
            """)
            cart_items_sql = conn.execute(cart_items_query).fetchone()[0]
            
            if 'variant_id' not in cart_items_sql:
                print("Adding variant_id column to cart_items table...")
                conn.execute(text("""
                    ALTER TABLE cart_items 
                    ADD COLUMN variant_id INTEGER
                    REFERENCES product_variant (id)
                """))
                print("Added variant_id column to cart_items table")
            else:
                print("variant_id column already exists in cart_items table")
            
            conn.commit()
            print("All tables created successfully")
            
        except Exception as e:
            print(f"Error creating tables: {str(e)}")
        finally:
            conn.close()

if __name__ == "__main__":
    create_product_tables()
