from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Category
from forms import CategoryForm
from slugify import slugify
from functools import wraps
from models import db, Category, User, Order  

admin = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@admin.route('/categories')
@admin_required
def categories():
    """List all categories in a tree view."""
    # Get all categories ordered by name
    categories = Category.query.order_by(Category.name).all()
    return render_template('admin/categories.html', categories=categories)

@admin.route('/categories/add', methods=['GET', 'POST'])
@admin_required
def add_category():
    form = CategoryForm()
    # Populate parent choices with existing categories
    form.parent_id.choices = [(0, 'None (Top Level)')] + [(c.id, c.name) for c in Category.query.order_by(Category.name).all()]
    
    if form.validate_on_submit():
        slug = slugify(form.name.data)
        # Check if slug already exists
        if Category.query.filter_by(slug=slug).first():
            flash('A category with this slug already exists. Please choose a different name.', 'danger')
            return render_template('admin/category_form.html', form=form, title='Add Category')
        
        category = Category(
            name=form.name.data,
            slug=slug,
            description=form.description.data,
            parent_id=form.parent_id.data if form.parent_id.data != 0 else None,
            image_url=form.image_url.data,
            is_active=form.is_active.data
        )
        db.session.add(category)
        db.session.commit()
        flash('Category added successfully.', 'success')
        return redirect(url_for('admin.categories'))
    
    return render_template('admin/category_form.html', form=form, title='Add Category')

@admin.route('/categories/edit/<int:id>', methods=['GET', 'POST'])
@admin_required
def edit_category(id):
    category = Category.query.get_or_404(id)
    form = CategoryForm(obj=category)
    # Populate parent choices, excluding itself and its descendants to prevent cycles
    # For simplicity, we'll exclude itself only; you can later improve.
    form.parent_id.choices = [(0, 'None (Top Level)')] + [(c.id, c.name) for c in Category.query.filter(Category.id != id).order_by(Category.name).all()]
    
    if form.validate_on_submit():
        # Update slug if name changed
        if form.name.data != category.name:
            category.slug = slugify(form.name.data)
            # Check uniqueness
            if Category.query.filter(Category.id != id, Category.slug == category.slug).first():
                flash('A category with this slug already exists. Please choose a different name.', 'danger')
                return render_template('admin/category_form.html', form=form, title='Edit Category')
        
        category.name = form.name.data
        category.description = form.description.data
        category.parent_id = form.parent_id.data if form.parent_id.data != 0 else None
        category.image_url = form.image_url.data
        category.is_active = form.is_active.data
        db.session.commit()
        flash('Category updated successfully.', 'success')
        return redirect(url_for('admin.categories'))
    
    # Pre-select parent in form
    form.parent_id.data = category.parent_id or 0
    return render_template('admin/category_form.html', form=form, title='Edit Category')

@admin.route('/categories/delete/<int:id>', methods=['POST'])
@admin_required
def delete_category(id):
    category = Category.query.get_or_404(id)
    # Check if category has children
    if category.children:
        flash('Cannot delete category with subcategories. Please delete or move them first.', 'danger')
    else:
        db.session.delete(category)
        db.session.commit()
        flash('Category deleted successfully.', 'success')
    return redirect(url_for('admin.categories'))

@admin.route('/users')
@admin_required
def users():
    """List all users with options to suspend/activate and verify email."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/toggle/<int:user_id>', methods=['POST'])
@admin_required
def toggle_user_status(user_id):
    """Suspend or activate a user account."""
    user = User.query.get_or_404(user_id)
    # Prevent admin from suspending themselves
    if user.is_admin and user.id == current_user.id:
        flash('You cannot suspend your own account.', 'danger')
        return redirect(url_for('admin.users'))
    
    if user.account_status == 'active':
        user.account_status = 'suspended'
        flash(f'User {user.username} has been suspended.', 'success')
    else:
        user.account_status = 'active'
        flash(f'User {user.username} has been activated.', 'success')
    
    db.session.commit()
    return redirect(url_for('admin.users'))

@admin.route('/users/verify/<int:user_id>', methods=['POST'])
@admin_required
def verify_user(user_id):
    """Manually verify a user's email."""
    user = User.query.get_or_404(user_id)
    user.email_verified = True
    db.session.commit()
    flash(f'User {user.username} email verified.', 'success')
    return redirect(url_for('admin.users'))

@admin.route('/orders')
@admin_required
def orders():
    """View all orders in the system."""
    orders = Order.query.order_by(Order.created_at.desc()).all()
    return render_template('admin/orders.html', orders=orders)