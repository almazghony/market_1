from flask_login import current_user
from flask_wtf import FlaskForm
from flask_wtf.file import FileAllowed, FileField
from wtforms import EmailField, PasswordField, StringField, SubmitField, TextAreaField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError
import re  # For password strength validation

from market.models import User

# Custom validator for password strength
def validate_password_strength(form, field):
    password = field.data
    if not re.match(r"^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$", password):
        raise ValidationError(
            "Password must contain at least one uppercase letter, one lowercase letter, one number, and one special character."
        )

# Form for user registration
class RegisterForm(FlaskForm):
    # Custom validator for checking if the username already exists
    def validate_username(self, username_to_check):
        if User.query.filter_by(username=username_to_check.data).first():
            raise ValidationError("Username already exists! Please choose a different username.")

    # Custom validator for checking if the email address already exists
    def validate_email_address(self, email_address_to_check):
        if User.query.filter_by(email_address=email_address_to_check.data).first():
            raise ValidationError("Email Address already exists! Please use a different email.")

    # Define form fields with validators
    name = StringField(
        label="Name:", validators=[Length(min=2, max=30), DataRequired()]
    )
    email_address = EmailField(
        label="Email Address:", validators=[Length(max=64), DataRequired(), Email(message="Please enter a valid email address.")]
    )
    password1 = PasswordField(
        label="Password:", validators=[Length(min=8, max=16), DataRequired(), validate_password_strength]
    )
    password2 = PasswordField(
        label="Confirm Password:", validators=[EqualTo("password1", message="Passwords must match."), DataRequired()]
    )
    mobile_number1 = StringField(label="Mobile", validators=[DataRequired()])
    mobile_number2 = StringField(label="Mobile 2 (Optional)")
    submit = SubmitField(label="Create Account")  # Submit button for registration


# Form for user login
class LoginForm(FlaskForm):
    email_address = EmailField(
        label="Email", validators=[Length(max=64), DataRequired(), Email(message="Please enter a valid email address.")]
    )
    password = PasswordField(
        label="Password:", validators=[Length(min=8, max=64), DataRequired()]
    )
    submit = SubmitField(label="Login")  # Submit button for login


# Form for removing an account or item
class RemoveForm(FlaskForm):
    submit = SubmitField(label="Remove")  # Submit button for removal action


# Form for updating user details
class UpdateForm(FlaskForm):
    name = StringField(
        label="Name:", validators=[Length(min=2, max=30), DataRequired()]
    )
    email_address = EmailField(
        label="Email Address:", validators=[Length(max=64), DataRequired(), Email(message="Please enter a valid email address.")]
    )
    mobile_number1 = StringField(label="Mobile", validators=[DataRequired()])
    mobile_number2 = StringField(label="Mobile 2 (optional)", validators=[])
    state = TextAreaField(label="State (optional)", validators=[Length(max=200)])  # Optional state message
    submit = SubmitField(label="Update information")  # Submit button for update
    picture = FileField(
        "Update Profile Picture", validators=[FileAllowed(["jpeg", "png", "jpg"], message="Only JPEG, PNG, and JPG files are allowed.")]
    )  # Field for profile picture upload

    # Custom validator for email address in the update form
    def validate_email_address(self, email_address_to_check):
        if email_address_to_check.data != current_user.email_address:
            if User.query.filter_by(email_address=email_address_to_check.data).first():
                raise ValidationError("Email Address already exists! Please use a different email.")

    # Custom validator for primary mobile number in the update form
    def validate_mobile_number1(self, mobile_number1_to_check):
        if mobile_number1_to_check.data != current_user.mobile_number1:
            if User.query.filter_by(mobile_number1=mobile_number1_to_check.data).first():
                raise ValidationError("Mobile Number already exists! Please use a different number.")

    # Custom validator for secondary mobile number in the update form
    def validate_mobile_number2(self, mobile_number2_to_check):
        if mobile_number2_to_check.data != current_user.mobile_number2:
            if User.query.filter_by(mobile_number2=mobile_number2_to_check.data).first():
                raise ValidationError("Mobile Number already exists! Please use a different number.")


# Form for password reset request
class ResetForm(FlaskForm):
    email_address = StringField(
        "Email", validators=[Length(max=64), DataRequired(), Email(message="Please enter a valid email address.")]
    )
    submit = SubmitField("Request Password Reset")  # Submit button for password reset request


# Form for changing the password
class ChangePasswordForm(FlaskForm):
    new_password = PasswordField(
        "New Password", validators=[Length(min=8, max=16), DataRequired(), validate_password_strength]
    )
    confirm_password = PasswordField(
        "Confirm Password",
        validators=[Length(min=8, max=16), DataRequired(), EqualTo("new_password", message="Passwords must match.")],
    )
    submit = SubmitField("Change Password")  # Submit button for password change