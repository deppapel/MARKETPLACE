from flask import Blueprint, render_template, request
from models import Service, Category
from sqlalchemy import or_

marketplace = Blueprint('marketplace', __name__)

@marketplace.route('/marketplace')
def index():
    # Base query: only published services
    query = Service.query.filter_by(status='published')

    # Search by keyword (title or description)
    q = request.args.get('q', '')
    if q:
        query = query.filter(
            or_(Service.title.ilike(f'%{q}%'), Service.description.ilike(f'%{q}%'))
        )

    # Filter by category
    category_id = request.args.get('category', type=int)
    if category_id:
        query = query.filter_by(category_id=category_id)

    # Filter by price range
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    if min_price is not None:
        query = query.filter(Service.price >= min_price)
    if max_price is not None:
        query = query.filter(Service.price <= max_price)

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 6  # Number of services per page
    pagination = query.order_by(Service.created_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    services = pagination.items

    # Get all active categories for filter dropdown
    categories = Category.query.filter_by(is_active=True).all()

    return render_template(
        'marketplace/index.html',
        services=services,
        pagination=pagination,
        categories=categories,
        selected_category=category_id,
        q=q,
        min_price=min_price,
        max_price=max_price
    )

@marketplace.route('/service/<slug>')
def detail(slug):
    service = Service.query.filter_by(slug=slug, status='published').first_or_404()
    # Increment view count (we'll implement later)
    return render_template('marketplace/detail.html', service=service)