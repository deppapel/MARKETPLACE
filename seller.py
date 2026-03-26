from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user
from models import db, Service, ServiceImage, Category
from forms import ServiceForm
from werkzeug.utils import secure_filename
from slugify import slugify
from functools import wraps
import os

seller = Blueprint('seller', __name__, url_prefix='/seller')

def seller_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_seller:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

@seller.route('/services')
@seller_required
def services():
    """List all services for the logged-in seller."""
    services = Service.query.filter_by(seller_id=current_user.id).order_by(Service.created_at.desc()).all()
    return render_template('seller/services.html', services=services)

@seller.route('/services/add', methods=['GET', 'POST'])
@seller_required
def add_service():
    form = ServiceForm()
    # Populate category choices (only active categories)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(is_active=True).order_by(Category.name).all()]
    
    if form.validate_on_submit():
        # Generate a unique slug from the title
        base_slug = slugify(form.title.data)
        slug = base_slug
        counter = 1
        while Service.query.filter_by(slug=slug).first():
            slug = f"{base_slug}-{counter}"
            counter += 1

        # Create new service
        service = Service(
            seller_id=current_user.id,
            category_id=form.category_id.data,
            title=form.title.data,
            slug=slug,
            description=form.description.data,
            price=form.price.data,
            delivery_time=form.delivery_time.data,
            requirements=form.requirements.data,
            status=form.status.data
        )
        db.session.add(service)
        db.session.commit()
        
        # Handle image upload(s)
        if form.images.data:
            files = request.files.getlist('images')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    img = ServiceImage(service_id=service.id, image_url=filename)
                    db.session.add(img)
            db.session.commit()
        
        flash('Service added successfully.', 'success')
        return redirect(url_for('seller.services'))
    
    return render_template('seller/service_form.html', form=form, title='Add Service')

@seller.route('/services/edit/<int:id>', methods=['GET', 'POST'])
@seller_required
def edit_service(id):
    service = Service.query.get_or_404(id)
    # Ensure the service belongs to the current seller
    if service.seller_id != current_user.id:
        flash('You do not have permission to edit this service.', 'danger')
        return redirect(url_for('seller.services'))
    
    form = ServiceForm(obj=service)
    form.category_id.choices = [(c.id, c.name) for c in Category.query.filter_by(is_active=True).order_by(Category.name).all()]
    
    if form.validate_on_submit():
        # If title changed, update slug (and ensure uniqueness)
        if form.title.data != service.title:
            base_slug = slugify(form.title.data)
            slug = base_slug
            counter = 1
            while Service.query.filter(Service.id != id, Service.slug == slug).first():
                slug = f"{base_slug}-{counter}"
                counter += 1
            service.slug = slug

        service.title = form.title.data
        service.description = form.description.data
        service.price = form.price.data
        service.delivery_time = form.delivery_time.data
        service.requirements = form.requirements.data
        service.category_id = form.category_id.data
        service.status = form.status.data
        db.session.commit()
        
        # Handle new image uploads (optional)
        if form.images.data:
            files = request.files.getlist('images')
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                    img = ServiceImage(service_id=service.id, image_url=filename)
                    db.session.add(img)
            db.session.commit()
        
        flash('Service updated successfully.', 'success')
        return redirect(url_for('seller.services'))
    
    return render_template('seller/service_form.html', form=form, title='Edit Service')

@seller.route('/services/delete/<int:id>', methods=['POST'])
@seller_required
def delete_service(id):
    service = Service.query.get_or_404(id)
    if service.seller_id != current_user.id:
        flash('You do not have permission to delete this service.', 'danger')
        return redirect(url_for('seller.services'))
    
    # Delete associated images from filesystem and DB
    for img in service.images:
        file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img.image_url)
        if os.path.exists(file_path):
            os.remove(file_path)
        db.session.delete(img)
    
    db.session.delete(service)
    db.session.commit()
    flash('Service deleted successfully.', 'success')
    return redirect(url_for('seller.services'))