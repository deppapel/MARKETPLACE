from flask import Blueprint, render_template, redirect, url_for, flash, request  # added request
from flask_login import login_required, current_user
from models import db, Notification

notifications = Blueprint('notifications', __name__, url_prefix='/notifications')

@notifications.route('/')
@login_required
def view_all():
    notifs = Notification.query.filter_by(user_id=current_user.id).order_by(Notification.created_at.desc()).all()
    return render_template('notifications/all.html', notifications=notifs)

@notifications.route('/mark/<int:notif_id>')
@login_required
def mark_read(notif_id):
    notif = Notification.query.get_or_404(notif_id)
    if notif.user_id != current_user.id:
        flash('You cannot access this notification.', 'danger')
        return redirect(url_for('main.home'))
    notif.is_read = True
    db.session.commit()
    # Redirect based on notification type (optional)
    if notif.type == 'message':
        return redirect(url_for('messaging.inbox'))
    elif notif.type == 'order_update':
        return redirect(url_for('orders.buyer_orders'))
    else:
        return redirect(url_for('notifications.view_all'))

@notifications.route('/mark-all-read', methods=['POST'])
@login_required
def mark_all_read():
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    flash('All notifications marked as read.', 'success')
    return redirect(request.referrer or url_for('notifications.view_all'))