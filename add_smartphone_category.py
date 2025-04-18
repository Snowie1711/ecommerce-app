from app import create_app
from models import db, Category

app = create_app()

def add_smartphone_category():
    with app.app_context():
        # Check if Smartphone category already exists
        smartphone_cat = Category.query.filter_by(name='Smartphone').first()
        if not smartphone_cat:
            # Create new category
            smartphone_cat = Category(
                name='Smartphone',
                slug='smartphone',
                description='Mobile phones and smartphones',
                has_sizes=False
            )
            db.session.add(smartphone_cat)
            try:
                db.session.commit()
                print("Smartphone category added successfully!")
            except Exception as e:
                db.session.rollback()
                print(f"Error adding category: {str(e)}")
        else:
            print("Smartphone category already exists!")

if __name__ == '__main__':
    add_smartphone_category()