from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from utils import payment_required
from models import db, Dispute, DisputeMessage, OrderItem, Notification, User
from functools import wraps
from datetime import datetime

disputes = Blueprint('disputes', __name__, url_prefix='/disputes')

def admin_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        if not current_user.is_admin:
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

def dispute_participant_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        dispute_id = kwargs.get('dispute_id')
        dispute = Dispute.query.get_or_404(dispute_id)
        if current_user.id not in [dispute.raised_by_id, dispute.order_item.seller_id, dispute.order_item.order.buyer_id]:
            if not current_user.is_admin:
                flash('You cannot access this dispute.', 'danger')
                return redirect(url_for('main.home'))
        return f(*args, **kwargs)
    return decorated_function

@disputes.route('/raise/<int:order_item_id>', methods=['GET', 'POST'])
@login_required
@payment_required
def raise_dispute(order_item_id):
    order_item = OrderItem.query.get_or_404(order_item_id)
    # Check if user is either buyer or seller of this item
    if current_user.id not in [order_item.order.buyer_id, order_item.seller_id]:
        flash('You cannot raise a dispute on this order.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_item.order.id))
    # Check if dispute already exists
    existing = Dispute.query.filter_by(order_item_id=order_item_id).first()
    if existing:
        flash('A dispute for this item already exists.', 'info')
        return redirect(url_for('disputes.view_dispute', dispute_id=existing.id))

    # Determine the other party and reason choices based on who is raising
    if current_user.id == order_item.order.buyer_id:
        against_id = order_item.seller_id
        reason_choices = [
            ('service_not_delivered', 'Service not delivered'),
            ('not_as_described', 'Not as described'),
            ('late_delivery', 'Late delivery'),
            ('seller_unresponsive', 'Seller unresponsive'),
            ('other', 'Other')
        ]
    else:  # current user is seller
        against_id = order_item.order.buyer_id
        reason_choices = [
            ('buyer_unresponsive', 'Buyer unresponsive'),
            ('late_payment', 'Late payment'),
            ('wrong_requirements', 'Wrong requirements provided'),
            ('buyer_cancelled', 'Buyer cancelled after work started'),
            ('other', 'Other')
        ]

    if request.method == 'POST':
        reason = request.form.get('reason')
        description = request.form.get('description')
        if not reason or not description:
            flash('Please provide both reason and description.', 'danger')
        else:
            dispute = Dispute(
                order_item_id=order_item.id,
                raised_by_id=current_user.id,
                against_id=against_id,
                reason=reason,
                description=description,
                status='open'
            )
            db.session.add(dispute)
            db.session.commit()

            # Notify the other party
            notif = Notification(
                user_id=against_id,
                type='dispute',
                title='Dispute Raised Against You',
                content=f'A dispute has been raised by the {"buyer" if current_user.id == order_item.order.buyer_id else "seller"} regarding order #{order_item.order.order_number}, service: {order_item.service.title}. Reason: {reason}'
            )
            db.session.add(notif)

            # Notify all admins
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                notif = Notification(
                    user_id=admin.id,
                    type='dispute',
                    title='New Dispute Raised',
                    content=f'Dispute #{dispute.id} on order #{order_item.order.order_number}'
                )
                db.session.add(notif)
            db.session.commit()

            flash('Dispute raised successfully.', 'success')
            return redirect(url_for('disputes.view_dispute', dispute_id=dispute.id))

    return render_template('disputes/raise.html', order_item=order_item, reason_choices=reason_choices)

@disputes.route('/<int:dispute_id>')
@login_required
@payment_required
@dispute_participant_required
def view_dispute(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    # Filter messages based on visibility
    if current_user.is_admin:
        messages = dispute.messages  # all
    else:
        messages = [m for m in dispute.messages if m.recipient_id is None or m.recipient_id == current_user.id]
    return render_template('disputes/view.html', dispute=dispute, messages=messages)

@disputes.route('/<int:dispute_id>/message', methods=['POST'])
@login_required
@dispute_participant_required
def add_message(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    content = request.form.get('message')
    recipient_id = request.form.get('recipient_id')

    if content:
        msg = DisputeMessage(
            dispute_id=dispute.id,
            sender_id=current_user.id,
            message=content
        )
        # If admin, set recipient_id if provided and not 'public'
        if current_user.is_admin and recipient_id:
            if recipient_id == 'public':
                msg.recipient_id = None
            else:
                try:
                    msg.recipient_id = int(recipient_id)
                except ValueError:
                    flash('Invalid recipient selected.', 'danger')
                    return redirect(url_for('disputes.view_dispute', dispute_id=dispute.id))
        else:
            msg.recipient_id = None

        db.session.add(msg)

        # Notify relevant parties (based on recipient)
        if msg.recipient_id:
            # Private message – notify only that recipient (if not sender)
            if msg.recipient_id != current_user.id:
                notif = Notification(
                    user_id=msg.recipient_id,
                    type='dispute',
                    title=f'Private message in Dispute #{dispute.id}',
                    content=content[:50] + '...'
                )
                db.session.add(notif)
        else:
            # Public message – notify all participants except sender
            participants = set()
            participants.add(dispute.raised_by_id)
            participants.add(dispute.against_id)
            # Add admins
            admins = User.query.filter_by(role='admin').all()
            for a in admins:
                participants.add(a.id)
            participants.discard(current_user.id)
            for uid in participants:
                notif = Notification(
                    user_id=uid,
                    type='dispute',
                    title=f'New message in Dispute #{dispute.id}',
                    content=content[:50] + '...'
                )
                db.session.add(notif)

        db.session.commit()
        flash('Message sent.', 'success')
    return redirect(url_for('disputes.view_dispute', dispute_id=dispute.id))

@disputes.route('/<int:dispute_id>/status', methods=['POST'])
@login_required
@admin_required
def update_status(dispute_id):
    dispute = Dispute.query.get_or_404(dispute_id)
    new_status = request.form.get('status')
    resolution_notes = request.form.get('resolution_notes')
    if new_status in ['under_review', 'resolved', 'escalated']:
        dispute.status = new_status
        if new_status == 'resolved':
            dispute.resolved_at = datetime.utcnow()
        if resolution_notes:
            dispute.resolution_notes = resolution_notes
        db.session.commit()

        # Notify participants
        participants = set()
        participants.add(dispute.raised_by_id)
        participants.add(dispute.order_item.seller_id)
        participants.add(dispute.order_item.order.buyer_id)
        for uid in participants:
            if uid != current_user.id:
                notif = Notification(
                    user_id=uid,
                    type='dispute',
                    title=f'Dispute #{dispute.id} status updated',
                    content=f'Status: {new_status}'
                )
                db.session.add(notif)
        db.session.commit()
        flash('Dispute status updated.', 'success')
    else:
        flash('Invalid status.', 'danger')
    return redirect(url_for('disputes.view_dispute', dispute_id=dispute.id))

@disputes.route('/admin')
@admin_required
def admin_disputes():
    """List all disputes for admin."""
    disputes = Dispute.query.order_by(Dispute.created_at.desc()).all()
    return render_template('disputes/admin_list.html', disputes=disputes)