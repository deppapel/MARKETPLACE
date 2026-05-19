from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def payment_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        if not current_user.registration_fee_paid:
            flash('Please pay the registration fee in your profile page to access this feature.', 'warning')
            return redirect(url_for('marketplace.index'))
        return f(*args, **kwargs)
    return decorated_function