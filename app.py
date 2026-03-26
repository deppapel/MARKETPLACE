from flask import Flask, redirect, url_for, send_from_directory, current_app
from config import Config
from models import db
from flask_login import LoginManager, current_user
from flask_mail import Mail
import os

# Import blueprints
from admin import admin as admin_blueprint
from seller import seller as seller_blueprint
from auth import auth as auth_blueprint
from main import main as main_blueprint
from marketplace import marketplace as marketplace_blueprint
from orders import orders as orders_blueprint
from reviews import reviews as reviews_blueprint
from cart import cart as cart_blueprint
from messaging import messaging as messaging_blueprint
from notifications import notifications as notifications_blueprint
from disputes import disputes as disputes_blueprint
from mpesa import mpesa as mpesa_blueprint

mail = Mail()

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize extensions
    mail.init_app(app)
    db.init_app(app)

    # Create upload folder if it doesn't exist
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    # Register blueprints
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(seller_blueprint)
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(main_blueprint)
    app.register_blueprint(marketplace_blueprint)
    app.register_blueprint(orders_blueprint)
    app.register_blueprint(reviews_blueprint)
    app.register_blueprint(cart_blueprint)
    app.register_blueprint(messaging_blueprint)
    app.register_blueprint(notifications_blueprint)
    app.register_blueprint(disputes_blueprint)
    app.register_blueprint(mpesa_blueprint)
    
    # Setup Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

    # Route to serve uploaded files
    @app.route('/uploads/<filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('marketplace.index'))

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    app.run(debug=True)