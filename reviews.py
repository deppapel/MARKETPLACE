from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Review, OrderItem, Notification  # added Notification
from forms import ReviewForm
from functools import wraps
from datetime import datetime

reviews = Blueprint('reviews', __name__, url_prefix='/reviews')

def seller_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_seller:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def buyer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_buyer:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@reviews.route('/add/<int:order_item_id>', methods=['GET', 'POST'])
@buyer_required
def add_review(order_item_id):
    order_item = OrderItem.query.get_or_404(order_item_id)
    # Check if this order item belongs to the current user
    if order_item.order.buyer_id != current_user.id:
        flash('You cannot review this order.', 'danger')
        return redirect(url_for('main.home'))
    # Check if order is completed
    if order_item.order.status != 'completed':
        flash('You can only review completed orders.', 'warning')
        return redirect(url_for('orders.order_detail', order_id=order_item.order.id))
    # Check if review already exists
    if order_item.review:
        flash('You have already reviewed this service.', 'info')
        return redirect(url_for('orders.order_detail', order_id=order_item.order.id))

    form = ReviewForm()
    if form.validate_on_submit():
        review = Review(
            order_item_id=order_item.id,
            buyer_id=current_user.id,
            seller_id=order_item.seller_id,
            rating=form.rating.data,
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()

        # Notify seller about the new review
        notif = Notification(
            user_id=review.seller_id,
            type='review',
            title='New Review Received',
            content=f'{current_user.full_name or current_user.username} left a {review.rating}/5 review on your service "{order_item.service.title}".'
        )
        db.session.add(notif)
        db.session.commit()

        flash('Review submitted successfully!', 'success')
        return redirect(url_for('marketplace.detail', slug=order_item.service.slug))
    return render_template('reviews/add.html', form=form, order_item=order_item)

@reviews.route('/edit/<int:review_id>', methods=['GET', 'POST'])
@login_required
def edit_review(review_id):
    review = Review.query.get_or_404(review_id)
    # Only the buyer who wrote the review can edit
    if review.buyer_id != current_user.id:
        flash('You cannot edit this review.', 'danger')
        return redirect(url_for('main.home'))
    form = ReviewForm(obj=review)
    if form.validate_on_submit():
        review.rating = form.rating.data
        review.comment = form.comment.data
        review.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Your review has been updated.', 'success')
        return redirect(url_for('marketplace.detail', slug=review.order_item.service.slug))
    return render_template('reviews/edit.html', form=form, review=review)

@reviews.route('/delete/<int:review_id>', methods=['POST'])
@login_required
def delete_review(review_id):
    review = Review.query.get_or_404(review_id)
    if review.buyer_id != current_user.id:
        flash('You cannot delete this review.', 'danger')
        return redirect(url_for('main.home'))
    service_slug = review.order_item.service.slug
    db.session.delete(review)
    db.session.commit()
    flash('Your review has been deleted.', 'success')
    return redirect(url_for('marketplace.detail', slug=service_slug))

@reviews.route('/seller')
@seller_required
def seller_reviews():
    """Show all reviews received by the current seller."""
    reviews = Review.query.filter_by(seller_id=current_user.id).order_by(Review.created_at.desc()).all()
    return render_template('reviews/seller_reviews.html', reviews=reviews)