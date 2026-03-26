from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, TextAreaField, SubmitField, RadioField, SelectField,DecimalField, IntegerField, FileField
from wtforms.widgets import ListWidget, CheckboxInput
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional, NumberRange
import re

def phone_number_check(form, field):
    if not re.match(r'^[\d\s\+\-]+$', field.data):
        raise ValidationError('Please enter a valid phone number (digits, spaces, +, -).')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), phone_number_check])
    password = PasswordField('Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    role = RadioField(
        'I want to register as:',
        choices=[('buyer', 'Buyer'), ('seller', 'Seller')],
        validators=[DataRequired()]
    )
    submit = SubmitField('Register')

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    full_name = StringField('Full Name', validators=[DataRequired(), Length(max=120)])
    phone_number = StringField('Phone Number', validators=[DataRequired(), phone_number_check])
    bio = TextAreaField('Bio', validators=[Optional(), Length(max=500)])
    avatar_url = StringField('Avatar URL', validators=[Optional(), Length(max=200)])
    submit = SubmitField('Update Profile')


class CategoryForm(FlaskForm):
    name = StringField('Category Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional(), Length(max=500)])
    parent_id = SelectField('Parent Category', coerce=int, validators=[Optional()])
    image_url = StringField('Image URL', validators=[Optional(), Length(max=200)])
    is_active = BooleanField('Active', default=True)
    submit = SubmitField('Save')    


class ServiceForm(FlaskForm):
    title = StringField('Service Title', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired(), Length(max=5000)])
    price = DecimalField('Price ($)', validators=[DataRequired(), NumberRange(min=0)])
    delivery_time = IntegerField('Delivery Time (days)', validators=[DataRequired(), NumberRange(min=1)])
    requirements = TextAreaField('Requirements from Buyer', validators=[Optional(), Length(max=2000)])
    category_id = SelectField('Category', coerce=int, validators=[DataRequired()])
    status = SelectField('Status', choices=[('draft', 'Draft'), ('published', 'Published')], default='draft')
    # For image uploads (we'll handle multiple images separately)
    images = FileField('Upload Images', validators=[Optional()])
    submit = SubmitField('Save Service')

class ReviewForm(FlaskForm):
    rating = IntegerField('Rating (1-5)', validators=[DataRequired(), NumberRange(min=1, max=5)])
    comment = TextAreaField('Comment', validators=[DataRequired(), Length(min=5, max=500)])
    submit = SubmitField('Submit Review')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Send Reset Code')

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])  # hidden or read-only
    otp = StringField('Verification Code', validators=[DataRequired(), Length(min=6, max=6)])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Reset Password')