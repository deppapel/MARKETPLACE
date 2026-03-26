from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, session
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, EmailVerification  # Import EmailVerification model
from forms import RegistrationForm, LoginForm, ChangePasswordForm, ForgotPasswordForm, ResetPasswordForm
from flask_mail import Message
import random
from datetime import datetime, timedelta

auth = Blueprint('auth', __name__)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        # Check if user already exists
        existing_user = User.query.filter((User.username == form.username.data) | (User.email == form.email.data)).first()
        if existing_user:
            flash('A user with that username or email already exists.', 'danger')
            return redirect(url_for('auth.register'))

        # Create new user with email_verified = False
        user = User(
            username=form.username.data,
            email=form.email.data,
            full_name=form.full_name.data,
            phone_number=form.phone_number.data,
            role=form.role.data,
            email_verified=False
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        # Generate OTP and send email
        otp = str(random.randint(100000, 999999))
        expiry = datetime.utcnow() + timedelta(minutes=15)
        verification = EmailVerification(user_id=user.id, otp_code=otp, expires_at=expiry)
        db.session.add(verification)
        db.session.commit()

        # Send email using the mail instance from current_app
        try:
            msg = Message('Verify Your Email - Marketplace',
                          recipients=[user.email])
            msg.body = f'Your verification code is: {otp}\nThis code expires in 15 minutes.'
            # Get mail instance from Flask extensions
            mail = current_app.extensions['mail']
            mail.send(msg)
            flash('A verification code has been sent to your email.', 'info')
        except Exception as e:
            print(e)  # For debugging; remove in production
            flash('Error sending email. Please try again.', 'danger')
            # Optionally delete user or handle error
            return redirect(url_for('auth.register'))

        # Redirect to OTP verification page
        return redirect(url_for('auth.verify_otp', user_id=user.id))

    return render_template('register.html', form=form)

@auth.route('/verify-otp/<int:user_id>', methods=['GET', 'POST'])
def verify_otp(user_id):
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        flash('Email already verified. Please log in.', 'info')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        otp = request.form.get('otp')
        verification = EmailVerification.query.filter_by(user_id=user.id, otp_code=otp).first()
        if verification and verification.expires_at > datetime.utcnow():
            # Mark email as verified
            user.email_verified = True
            db.session.delete(verification)  # remove used OTP
            db.session.commit()
            flash('Email verified successfully! You can now log in.', 'success')
            return redirect(url_for('auth.login'))
        else:
            flash('Invalid or expired OTP. Please try again.', 'danger')
            return redirect(url_for('auth.verify_otp', user_id=user.id))

    return render_template('verify_otp.html', user_id=user_id, email=user.email)

@auth.route('/resend-otp/<int:user_id>')
def resend_otp(user_id):
    user = User.query.get_or_404(user_id)
    if user.email_verified:
        flash('Email already verified.', 'info')
        return redirect(url_for('auth.login'))

    # Delete old verifications
    EmailVerification.query.filter_by(user_id=user.id).delete()

    # Generate new OTP
    otp = str(random.randint(100000, 999999))
    expiry = datetime.utcnow() + timedelta(minutes=15)
    verification = EmailVerification(user_id=user.id, otp_code=otp, expires_at=expiry)
    db.session.add(verification)
    db.session.commit()

    # Send email
    try:
        msg = Message('Verify Your Email - Marketplace', recipients=[user.email])
        msg.body = f'Your new verification code is: {otp}\nThis code expires in 15 minutes.'
        mail = current_app.extensions['mail']
        mail.send(msg)
        flash('A new verification code has been sent.', 'info')
    except Exception as e:
        print(e)
        flash('Error sending email. Please try again later.', 'danger')

    return redirect(url_for('auth.verify_otp', user_id=user.id))

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            if not user.email_verified:
                flash('Please verify your email before logging in.', 'warning')
                return redirect(url_for('auth.verify_otp', user_id=user.id))
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Invalid username or password.', 'danger')
    return render_template('login.html', form=form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        # Verify current password
        if not current_user.check_password(form.current_password.data):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('auth.change_password'))
        # Set new password
        current_user.set_password(form.new_password.data)
        db.session.commit()
        flash('Your password has been updated.', 'success')
        return redirect(url_for('main.profile'))
    return render_template('change_password.html', form=form)

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            # Still show success to avoid email enumeration
            flash('If that email exists, a reset code has been sent.', 'info')
            return redirect(url_for('auth.forgot_password'))
        
        # Delete any existing OTPs for this user
        EmailVerification.query.filter_by(user_id=user.id).delete()
        
        # Generate OTP
        otp = str(random.randint(100000, 999999))
        expiry = datetime.utcnow() + timedelta(minutes=15)
        verif = EmailVerification(user_id=user.id, otp_code=otp, expires_at=expiry)
        db.session.add(verif)
        db.session.commit()

        # Send email
        try:
            msg = Message('Password Reset Code - Marketplace',
                          recipients=[user.email])
            msg.body = f'Your password reset code is: {otp}\nThis code expires in 15 minutes.'
            mail = current_app.extensions['mail']
            mail.send(msg)
            flash('A reset code has been sent to your email.', 'info')
            # Store email in session to prefill next form
            session['reset_email'] = user.email
            return redirect(url_for('auth.reset_password'))
        except Exception as e:
            print(e)
            flash('Error sending email. Please try again.', 'danger')
            return redirect(url_for('auth.forgot_password'))
    return render_template('forgot_password.html', form=form)

@auth.route('/reset-password', methods=['GET', 'POST'])
def reset_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    # Prefill email from session if available
    email = session.get('reset_email', '')
    form = ResetPasswordForm(email=email)
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if not user:
            flash('No account found with that email.', 'danger')
            return redirect(url_for('auth.forgot_password'))
        # Verify OTP
        verif = EmailVerification.query.filter_by(user_id=user.id, otp_code=form.otp.data).first()
        if not verif or verif.expires_at < datetime.utcnow():
            flash('Invalid or expired OTP.', 'danger')
            return redirect(url_for('auth.reset_password'))
        # Update password
        user.set_password(form.new_password.data)
        # Delete used OTP
        db.session.delete(verif)
        db.session.commit()
        # Clear session
        session.pop('reset_email', None)
        flash('Password reset successful. Please log in.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('reset_password.html', form=form, email=email)