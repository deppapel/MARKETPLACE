from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Cart, CartItem, Service, Order, OrderItem
from functools import wraps
from datetime import datetime
from utils import payment_required
import random
import string


cart = Blueprint('cart', __name__, url_prefix='/cart')

def buyer_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_buyer:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def get_or_create_cart(user_id):
    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()
    return cart

def generate_order_number():
    date_part = datetime.utcnow().strftime('%Y%m%d')
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    order_number = f"ORD-{date_part}-{random_part}"
    while Order.query.filter_by(order_number=order_number).first():
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        order_number = f"ORD-{date_part}-{random_part}"
    return order_number

@cart.route('/')
@buyer_required
def view_cart():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    return render_template('cart/view.html', cart=cart)

@cart.route('/add/<int:service_id>', methods=['POST'])
@buyer_required
@payment_required
def add_to_cart(service_id):
    service = Service.query.get_or_404(service_id)
    if service.status != 'published':
        flash('This service is not available.', 'danger')
        return redirect(url_for('marketplace.detail', slug=service.slug))

    cart = get_or_create_cart(current_user.id)
    # Check if already in cart
    cart_item = CartItem.query.filter_by(cart_id=cart.id, service_id=service_id).first()
    if cart_item:
        cart_item.quantity += 1
    else:
        cart_item = CartItem(cart_id=cart.id, service_id=service_id, quantity=1)
        db.session.add(cart_item)
    db.session.commit()
    flash('Service added to cart.', 'success')
    return redirect(url_for('marketplace.detail', slug=service.slug))

@cart.route('/remove/<int:item_id>', methods=['POST'])
@buyer_required
def remove_item(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id:
        flash('You cannot remove this item.', 'danger')
        return redirect(url_for('cart.view_cart'))
    db.session.delete(item)
    db.session.commit()
    flash('Item removed from cart.', 'success')
    return redirect(url_for('cart.view_cart'))

@cart.route('/update/<int:item_id>', methods=['POST'])
@buyer_required
def update_quantity(item_id):
    item = CartItem.query.get_or_404(item_id)
    if item.cart.user_id != current_user.id:
        flash('You cannot update this item.', 'danger')
        return redirect(url_for('cart.view_cart'))
    quantity = request.form.get('quantity', type=int)
    if quantity and quantity > 0:
        item.quantity = quantity
        db.session.commit()
        flash('Quantity updated.', 'success')
    else:
        flash('Invalid quantity.', 'danger')
    return redirect(url_for('cart.view_cart'))

@cart.route('/checkout', methods=['POST'])
@buyer_required
@payment_required
def checkout():
    cart = Cart.query.filter_by(user_id=current_user.id).first()
    if not cart or not cart.items:
        flash('Your cart is empty.', 'warning')
        return redirect(url_for('marketplace.index'))

    # Calculate total
    total = sum(item.service.price * item.quantity for item in cart.items)

    # Create order
    order = Order(
        buyer_id=current_user.id,
        order_number=generate_order_number(),
        status='paid',
        total_amount=total,
        payment_method='dummy',
        paid_at=datetime.utcnow()
    )
    db.session.add(order)
    db.session.flush()  # to get order.id

    # Create order items
    for item in cart.items:
        order_item = OrderItem(
            order_id=order.id,
            service_id=item.service_id,
            seller_id=item.service.seller_id,
            quantity=item.quantity,
            unit_price=item.service.price,
            total_price=item.service.price * item.quantity
        )
        db.session.add(order_item)

    # Clear cart
    CartItem.query.filter_by(cart_id=cart.id).delete()
    db.session.commit()

    flash('Order placed successfully!', 'success')
    return redirect(url_for('orders.order_detail', order_id=order.id))