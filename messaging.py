from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from utils import payment_required
from models import db, Conversation, ConversationParticipant, Message, Notification, Order
from datetime import datetime
from functools import wraps

messaging = Blueprint('messaging', __name__, url_prefix='/messages')

def participant_required(f):
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Assumes conversation_id is in kwargs
        conv_id = kwargs.get('conversation_id')
        conv = Conversation.query.get_or_404(conv_id)
        if not any(p.user_id == current_user.id for p in conv.participants):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function

@messaging.route('/')
@login_required
@payment_required
def inbox():
    """List all conversations for the current user."""
    participants = ConversationParticipant.query.filter_by(user_id=current_user.id).order_by(ConversationParticipant.last_read_at.desc()).all()
    convs = [p.conversation for p in participants]
    return render_template('messaging/inbox.html', conversations=convs)

@messaging.route('/<int:conversation_id>')
@login_required
@participant_required
def view_conversation(conversation_id):
    conv = Conversation.query.get_or_404(conversation_id)
    # Update last_read for current user
    participant = ConversationParticipant.query.filter_by(conversation_id=conversation_id, user_id=current_user.id).first()
    if participant:
        participant.last_read_at = datetime.utcnow()
        db.session.commit()
    # Mark messages as read
    for msg in conv.messages:
        if msg.sender_id != current_user.id and not msg.is_read:
            msg.is_read = True
    db.session.commit()
    return render_template('messaging/conversation.html', conversation=conv)

@messaging.route('/<int:conversation_id>/send', methods=['POST'])
@login_required
@participant_required
@payment_required
def send_message(conversation_id):
    content = request.form.get('content')
    if not content:
        flash('Message cannot be empty.', 'danger')
        return redirect(url_for('messaging.view_conversation', conversation_id=conversation_id))

    conv = Conversation.query.get(conversation_id)
    msg = Message(
        conversation_id=conversation_id,
        sender_id=current_user.id,
        content=content
    )
    db.session.add(msg)

    # Update last_read for sender
    participant = ConversationParticipant.query.filter_by(conversation_id=conversation_id, user_id=current_user.id).first()
    if participant:
        participant.last_read_at = datetime.utcnow()

    # Create notification for other participants
    for p in conv.participants:
        if p.user_id != current_user.id:
            notif = Notification(
                user_id=p.user_id,
                type='message',
                title='New Message',
                content=f'You have a new message from {current_user.full_name or current_user.username} in conversation about order #{conv.order_id if conv.order else "General"}'
            )
            db.session.add(notif)
    db.session.commit()
    return redirect(url_for('messaging.view_conversation', conversation_id=conversation_id))

@messaging.route('/start/<int:order_id>', methods=['GET', 'POST'])
@login_required
@payment_required
def start_conversation(order_id):
    order = Order.query.get_or_404(order_id)
    # Allowed participants: buyer and all sellers
    allowed_ids = [order.buyer_id] + list(set(item.seller_id for item in order.items))
    if current_user.id not in allowed_ids:
        flash('You cannot start a conversation for this order.', 'danger')
        return redirect(url_for('orders.order_detail', order_id=order_id))
    # Check if conversation already exists
    conv = Conversation.query.filter_by(order_id=order_id).first()
    if not conv:
        conv = Conversation(order_id=order_id)
        db.session.add(conv)
        db.session.flush()
        # Add all participants
        for uid in set(allowed_ids):
            cp = ConversationParticipant(conversation_id=conv.id, user_id=uid)
            db.session.add(cp)
        db.session.commit()
    return redirect(url_for('messaging.view_conversation', conversation_id=conv.id))

@messaging.route('/start/seller/<int:seller_id>', methods=['POST'])
@login_required
def start_conversation_with_seller(seller_id):
    if current_user.id == seller_id:
        flash('You cannot start a conversation with yourself.', 'danger')
        return redirect(url_for('marketplace.index'))

    # Check if conversation already exists between these two users
    # For simplicity, we'll create a new one each time – but we can avoid duplicates by checking existing convos where only these two are participants.
    # We'll do a simple check: any conversation with exactly these two participants (no order) – but that's complex. For now, create a new one.
    conv = Conversation()  # no order
    db.session.add(conv)
    db.session.flush()
    for uid in [current_user.id, seller_id]:
        cp = ConversationParticipant(conversation_id=conv.id, user_id=uid)
        db.session.add(cp)
    db.session.commit()
    return redirect(url_for('messaging.view_conversation', conversation_id=conv.id))