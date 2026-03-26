from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from forms import ProfileForm
from models import db, User, Order

main = Blueprint('main', __name__)

@main.route('/home')
@login_required
def home():
    # Redirect to role-specific dashboard
    if 'seller' in current_user.role.split(','):
        return redirect(url_for('main.seller_dashboard'))
    elif 'buyer' in current_user.role.split(','):
        return redirect(url_for('main.buyer_dashboard'))
    elif 'admin' in current_user.role.split(','):
        return redirect(url_for('main.admin_dashboard'))
    else:
        # Fallback (should not happen)
        return redirect(url_for('main.some_other_page'))

@main.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm()
    if form.validate_on_submit():
        # Update user fields
        current_user.username = form.username.data
        current_user.email = form.email.data
        current_user.full_name = form.full_name.data
        current_user.phone_number = form.phone_number.data
        current_user.bio = form.bio.data
        current_user.avatar_url = form.avatar_url.data
        db.session.commit()
        flash('Your profile has been updated.', 'success')
        return redirect(url_for('main.profile'))
    elif request.method == 'GET':
        # Pre-populate form with current user data
        form.username.data = current_user.username
        form.email.data = current_user.email
        form.full_name.data = current_user.full_name
        form.phone_number.data = current_user.phone_number
        form.bio.data = current_user.bio
        form.avatar_url.data = current_user.avatar_url
    return render_template('profile.html', form=form)

@main.route('/seller/dashboard')
@login_required
def seller_dashboard():
    if 'seller' not in current_user.role.split(','):
        return redirect(url_for('main.home'))
    return render_template('seller_dashboard.html', user=current_user)

@main.route('/buyer/dashboard')
@login_required
def buyer_dashboard():
    if 'buyer' not in current_user.role.split(','):
        return redirect(url_for('main.home'))
    return render_template('buyer_dashboard.html', user=current_user)

@main.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if 'admin' not in current_user.role.split(','):
        return redirect(url_for('main.home'))
    # Get user statistics
    total_users = User.query.count()
    buyers = User.query.filter(User.role.contains('buyer')).count()
    sellers = User.query.filter(User.role.contains('seller')).count()
    recent_orders = Order.query.order_by(Order.created_at.desc()).limit(3).all()
    return render_template('admin_dashboard.html', 
                           user=current_user, 
                           total_users=total_users, 
                           buyers=buyers, 
                           sellers=sellers,
                           recent_orders=recent_orders)