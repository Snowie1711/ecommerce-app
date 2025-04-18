from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from extensions import db
from models import Review, Product, Order
from models.order import OrderStatus
from datetime import datetime
from sqlalchemy.exc import IntegrityError

reviews_bp = Blueprint('reviews', __name__)

@reviews_bp.route('/api/products/<int:product_id>/reviews', methods=['POST'])
@login_required
def create_review(product_id):
    """Create a new review for a product"""
    try:
        # Get review data from request
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        rating = data.get('rating')
        comment = data.get('comment')
        order_id = data.get('order_id')

        # Validate required fields
        if not all([rating, comment, order_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Validate rating
        if not isinstance(rating, int) or rating < 1 or rating > 5:
            return jsonify({'error': 'Invalid rating. Must be between 1 and 5'}), 400

        # Check if product exists
        product = Product.query.get_or_404(product_id)

        # Check if order exists and belongs to user
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Check if order is delivered
        if order.status != OrderStatus.DELIVERED:
            return jsonify({'error': 'Can only review products from delivered orders'}), 400

        # Check if product was in this order
        order_items = [item.product_id for item in order.items]
        if product_id not in order_items:
            return jsonify({'error': 'Product not found in this order'}), 400

        # Create new review
        review = Review(
            user_id=current_user.id,
            product_id=product_id,
            order_id=order_id,
            rating=rating,
            comment=comment
        )

        db.session.add(review)
        db.session.commit()

        return jsonify(review.to_dict()), 201

    except IntegrityError:
        db.session.rollback()
        return jsonify({'error': 'You have already reviewed this product for this order'}), 400
    except Exception as e:
        current_app.logger.error(f"Error creating review: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Error creating review'}), 500

@reviews_bp.route('/api/products/<int:product_id>/reviews', methods=['GET'])
def get_product_reviews(product_id):
    """Get all reviews for a product"""
    try:
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 50)

        # Check if product exists
        product = Product.query.get_or_404(product_id)

        # Get paginated reviews
        reviews = Review.query.filter_by(product_id=product_id)\
            .order_by(Review.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        # Calculate average rating
        avg_rating = db.session.query(db.func.avg(Review.rating))\
            .filter(Review.product_id == product_id)\
            .scalar() or 0

        return jsonify({
            'reviews': [review.to_dict() for review in reviews.items],
            'total': reviews.total,
            'pages': reviews.pages,
            'current_page': reviews.page,
            'average_rating': float(avg_rating)
        })

    except Exception as e:
        current_app.logger.error(f"Error getting reviews: {str(e)}")
        return jsonify({'error': 'Error getting reviews'}), 500

@reviews_bp.route('/api/reviews/<int:review_id>', methods=['DELETE'])
@login_required
def delete_review(review_id):
    """Delete a review"""
    try:
        review = Review.query.get_or_404(review_id)

        # Check if user owns this review or is admin
        if review.user_id != current_user.id and not current_user.is_admin:
            return jsonify({'error': 'Unauthorized to delete this review'}), 403

        db.session.delete(review)
        db.session.commit()

        return jsonify({'message': 'Review deleted successfully'}), 200

    except Exception as e:
        current_app.logger.error(f"Error deleting review: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Error deleting review'}), 500

@reviews_bp.route('/api/orders/<int:order_id>/reviewed-products')
@login_required
def get_reviewed_products(order_id):
    """Get list of products that have been reviewed for this order"""
    try:
        # Check if order exists and belongs to user
        order = Order.query.get_or_404(order_id)
        if order.user_id != current_user.id:
            return jsonify({'error': 'Unauthorized'}), 403

        # Get all reviewed product IDs for this order
        reviewed_products = Review.query.filter_by(
            user_id=current_user.id,
            order_id=order_id
        ).with_entities(Review.product_id).all()

        reviewed_product_ids = [r[0] for r in reviewed_products]

        return jsonify({
            'reviewed_product_ids': reviewed_product_ids
        })

    except Exception as e:
        current_app.logger.error(f"Error getting reviewed products: {str(e)}")
        return jsonify({'error': 'Error getting reviewed products'}), 500