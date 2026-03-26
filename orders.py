from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Order, OrderItem, Service, User, Notification  # added Notification
from functools import wraps
import random
import string
from datetime import datetime

orders = Blueprint('orders', __name__, url_prefix='/orders')

def buyer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_buyer:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def seller_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_seller:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def generate_order_number():
    date_part = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    order_number = f"ORD-{date_part}-{random_part}"
    while Order.query.filter_by(order_number=order_number).first():
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        order_number = f"ORD-{date_part}-{random_part}"
    return order_number

def update_order_status(order):
    """Recalculate order status based on its items."""
    item_statuses = [item.status for item in order.items]
    if all(s == 'completed' for s in item_statuses):
        order.status = 'completed'
        order.completed_at = datetime.utcnow()
    elif any(s == 'in_progress' for s in item_statuses):
        order.status = 'in_progress'
    else:
        order.status = 'paid'  # all items still pending
    db.session.commit()

@orders.route('/create/<int:service_id>', methods=['POST'])
@buyer_required
def create_order(service_id):
    """Legacy single-service order (kept for compatibility)."""
    service = Service.query.get_or_404(service_id)
    if service.status != 'published':
        flash('This service is not available.', 'danger')
        return redirect(url_for('marketplace.detail', slug=service.slug))

    order = Order(
        buyer_id=current_user.id,
        order_number=generate_order_number(),
        status='paid',          # dummy payment
        total_amount=service.price,
        payment_method='dummy',
        paid_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()

    item = OrderItem(
        order_id=order.id,
        service_id=service.id,
        seller_id=service.seller_id,
        quantity=1,
        unit_price=service.price,
        total_price=service.price,
        status='pending'
    )
    db.session.add(item)
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('orders.order_detail', order_id=order.id))

@orders.route('/<int:order_id>')
@login_required
def order_detail(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id and not any(item.seller_id == current_user.id for item in order.items):
        flash('You do not have permission to view this order.', 'danger')
        return redirect(url_for('main.home'))
    return render_template('orders/detail.html', order=order)

@orders.route('/buyer/orders')
@buyer_required
def buyer_orders():
    orders = Order.query.filter_by(buyer_id=current_user.id).order_by(Order.created_at.desc()).all()
    return render_template('orders/buyer_orders.html', orders=orders)

@orders.route('/seller/orders')
@seller_required
def seller_orders():
    items = OrderItem.query.filter_by(seller_id=current_user.id).all()
    order_ids = set(item.order_id for item in items)
    orders = Order.query.filter(Order.id.in_(order_ids)).order_by(Order.created_at.desc()).all()
    return render_template('orders/seller_orders.html', orders=orders, current_user=current_user)

@orders.route('/item/<int:item_id>/status', methods=['POST'])
@login_required
def update_item_status(item_id):
    item = OrderItem.query.get_or_404(item_id)
    if item.seller_id != current_user.id:
        flash('You do not have permission to update this item.', 'danger')
        return redirect(url_for('orders.seller_orders'))
    new_status = request.form.get('status')
    if new_status in ['pending', 'in_progress', 'completed']:
        old_status = item.status
        item.status = new_status
        db.session.commit()
        update_order_status(item.order)

        # Notify buyer about the change
        notif = Notification(
            user_id=item.order.buyer_id,
            type='order_update',
            title='Order Item Status Updated',
            content=f'Item "{item.service.title}" in order #{item.order.order_number} changed from {old_status} to {new_status}.'
        )
        db.session.add(notif)
        db.session.commit()

        flash('Item status updated.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('orders.order_detail', order_id=item.order.id))

@orders.route('/cancel/<int:order_id>', methods=['POST'])
@login_required
def cancel_order(order_id):
    order = Order.query.get_or_404(order_id)
    if order.buyer_id != current_user.id:
        flash('You cannot cancel this order.', 'danger')
        return redirect(url_for('main.home'))
    if order.status == 'paid':   # allow cancellation only if not yet started
        order.status = 'cancelled'
        db.session.commit()

        # Notify all sellers that the order was cancelled
        for item in order.items:
            notif = Notification(
                user_id=item.seller_id,
                type='order_update',
                title='Order Cancelled',
                content=f'Order #{order.order_number} has been cancelled by the buyer.'
            )
            db.session.add(notif)
        db.session.commit()

        flash('Order cancelled.', 'success')
    else:
        flash('Order cannot be cancelled at this stage.', 'danger')
    return redirect(url_for('orders.order_detail', order_id=order.id))