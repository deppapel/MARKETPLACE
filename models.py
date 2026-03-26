from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    full_name = db.Column(db.String(120))
    phone_number = db.Column(db.String(20))
    avatar_url = db.Column(db.String(200))
    bio = db.Column(db.Text)
    role = db.Column(db.String(50), default='buyer')  # 'buyer', 'seller', 'admin', or 'buyer,seller'
    email_verified = db.Column(db.Boolean, default=False)
    account_status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    registration_fee_paid = db.Column(db.Boolean, default=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_buyer(self):
        return 'buyer' in self.role.split(',')

    @property
    def is_seller(self):
        return 'seller' in self.role.split(',')

    @property
    def is_admin(self):
        return 'admin' in self.role.split(',')

    @property
    def is_active(self):
        return self.account_status == 'active'
    
class Category(db.Model):
    __tablename__ = 'category'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    slug = db.Column(db.String(120), unique=True, nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    image_url = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))


class Service(db.Model):
    __tablename__ = 'service'
    id = db.Column(db.Integer, primary_key=True)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Numeric(10,2))
    delivery_time = db.Column(db.Integer)  # in days
    requirements = db.Column(db.Text)
    status = db.Column(db.String(20), default='draft')
    view_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    seller = db.relationship('User', backref='services')
    category = db.relationship('Category', backref='services')
    images = db.relationship('ServiceImage', backref='service', cascade='all, delete-orphan')
    order_items = db.relationship('OrderItem', back_populates='service')

    @property
    def average_rating(self):
        reviews = [item.review for item in self.order_items if item.review]
        if not reviews:
            return None
        return sum(r.rating for r in reviews) / len(reviews)

class ServiceImage(db.Model):
    __tablename__ = 'service_image'
    id = db.Column(db.Integer, primary_key=True)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    image_url = db.Column(db.String(200), nullable=False)
    sort_order = db.Column(db.Integer, default=0)


class Order(db.Model):
    __tablename__ = 'orders'
    id = db.Column(db.Integer, primary_key=True)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    status = db.Column(db.String(30), default='pending')
    total_amount = db.Column(db.Numeric(10,2))
    payment_method = db.Column(db.String(50))
    mpesa_receipt = db.Column(db.String(100))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    paid_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    buyer = db.relationship('User', foreign_keys=[buyer_id], backref='orders')
    items = db.relationship('OrderItem', backref='order', cascade='all, delete-orphan')
    conversations = db.relationship('Conversation', backref='order', cascade='all, delete-orphan')

    @property
    def messages(self):
        """Return all messages across conversations for this order."""
        msgs = []
        for conv in self.conversations:
            msgs.extend(conv.messages)
        return sorted(msgs, key=lambda m: m.created_at)

class Transaction(db.Model):
    __tablename__ = 'transaction'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    amount = db.Column(db.Numeric(10,2), nullable=False)
    mpesa_receipt = db.Column(db.String(100), unique=True)
    phone_number = db.Column(db.String(20))
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    transaction_type = db.Column(db.String(20))  # 'registration' or 'order'
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)

    user = db.relationship('User', backref='transactions')
    order = db.relationship('Order', backref='transactions')


class OrderItem(db.Model):
    __tablename__ = 'order_item'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)  # fixed
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # fixed
    quantity = db.Column(db.Integer, default=1)
    unit_price = db.Column(db.Numeric(10,2), nullable=False)
    total_price = db.Column(db.Numeric(10,2), nullable=False)
    status = db.Column(db.String(20), default='pending')
    
    service = db.relationship('Service', back_populates='order_items')
    seller = db.relationship('User', foreign_keys=[seller_id])


class Review(db.Model):
    __tablename__ = 'review'
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), unique=True, nullable=False)
    buyer_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    seller_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer)  # 1-5
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    order_item = db.relationship('OrderItem', backref=db.backref('review', uselist=False))
    buyer = db.relationship('User', foreign_keys=[buyer_id])
    seller = db.relationship('User', foreign_keys=[seller_id])


class Message(db.Model):
    __tablename__ = 'message'
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', back_populates='messages')
    sender = db.relationship('User', foreign_keys=[sender_id], backref='sent_messages')


class Notification(db.Model):
    __tablename__ = 'notification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  # fixed
    type = db.Column(db.String(50))
    title = db.Column(db.String(200))
    content = db.Column(db.Text)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='notifications')

class EmailVerification(db.Model):
    __tablename__ = 'email_verification'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref='verifications')    


class Cart(db.Model):
    __tablename__ = 'cart'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, unique=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('cart', uselist=False))
    items = db.relationship('CartItem', backref='cart', cascade='all, delete-orphan')

class CartItem(db.Model):
    __tablename__ = 'cart_item'
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('service.id'), nullable=False)
    quantity = db.Column(db.Integer, default=1)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    service = db.relationship('Service')

class Conversation(db.Model):
    __tablename__ = 'conversation'
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)

    participants = db.relationship('ConversationParticipant', back_populates='conversation', cascade='all, delete-orphan')
    messages = db.relationship('Message', back_populates='conversation', cascade='all, delete-orphan', order_by='Message.created_at')

class ConversationParticipant(db.Model):
    __tablename__ = 'conversation_participant'
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True)
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_read_at = db.Column(db.DateTime, default=datetime.utcnow)

    conversation = db.relationship('Conversation', back_populates='participants')
    user = db.relationship('User', backref='conversation_participations')

class Dispute(db.Model):
    __tablename__ = 'dispute'
    id = db.Column(db.Integer, primary_key=True)
    order_item_id = db.Column(db.Integer, db.ForeignKey('order_item.id'), nullable=False)
    raised_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  
    against_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    reason = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, under_review, resolved, escalated
    resolution_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, onupdate=datetime.utcnow)
    resolved_at = db.Column(db.DateTime)

    order_item = db.relationship('OrderItem', backref='disputes')
    raised_by = db.relationship('User', foreign_keys=[raised_by_id])
    against = db.relationship('User', foreign_keys=[against_id])

class DisputeMessage(db.Model):
    __tablename__ = 'dispute_message'
    id = db.Column(db.Integer, primary_key=True)
    dispute_id = db.Column(db.Integer, db.ForeignKey('dispute.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    recipient_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    dispute = db.relationship('Dispute', backref='messages')
    sender = db.relationship('User', foreign_keys=[sender_id])    
    recipient = db.relationship('User', foreign_keys=[recipient_id])

   