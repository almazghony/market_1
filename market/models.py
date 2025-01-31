from flask import current_app
from flask_login import UserMixin
from itsdangerous import URLSafeTimedSerializer as Serializer
import logging

from market import bcrypt, db, login_manager

# Set up logging
logger = logging.getLogger(__name__)

# Load user by ID for session management
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer(), primary_key=True)  # User ID
    name = db.Column(db.String(length=30), nullable=False)  # User's name
    email_address = db.Column(db.String(length=64), nullable=False, unique=True)  # Unique email
    password_hash = db.Column(db.String(), nullable=False)  # Hashed password
    mobile_number1 = db.Column(db.String(11), nullable=False)  # Primary mobile number
    mobile_number2 = db.Column(db.String(11))  # Optional secondary mobile number
    image_file = db.Column(db.String(20))  # Profile image filename
    state = db.Column(db.String(), default="Didn't write anything yet")  # User status message
    items = db.relationship("Item", backref="owned_user", lazy=True)  # Relationship to items owned
    is_verified = db.Column(db.Boolean, default=False)  # Email verification status

    @staticmethod
    def generate_verification_token(email, expiration=3600):
        """
        Generate a secure token for email verification.
        """
        try:
            serializer = Serializer(current_app.config["SECRET_KEY"])
            token = serializer.dumps({"email": email}, salt="1030204050")
            current_app.logger.debug(f"Generated verification token for {email}: {token}")
            return token
        except Exception as e:
            current_app.logger.error(f"Failed to generate verification token: {e}")
            raise

    @staticmethod
    def verify_email_token(token, expiration=3600):
        """
        Verify the email token and return the email if valid.
        """
        try:
            serializer = Serializer(current_app.config["SECRET_KEY"])
            data = serializer.loads(token, salt="1030204050", max_age=expiration)
            email = data["email"]
            current_app.logger.debug(f"Verified token for email: {email}")
            return email
        except Exception as e:
            current_app.logger.error(f"Token verification failed: {e}")
            return None

    def get_reset_token(self, expiration=3600):
        """
        Generate a secure token for password reset.
        """
        try:
            serializer = Serializer(current_app.config["SECRET_KEY"])
            token = serializer.dumps({"user_id": self.id}, salt="password-reset-salt")
            logger.debug(f"Generated reset token for user {self.id}: {token}")
            return token
        except Exception as e:
            logger.error(f"Failed to generate reset token: {e}")
            raise

    @staticmethod
    def verify_reset_token(token, expiration=3600):
        """
        Verify the reset token and return the user if valid.
        """
        try:
            serializer = Serializer(current_app.config["SECRET_KEY"])
            data = serializer.loads(token, salt="password-reset-salt", max_age=expiration)
            user_id = data["user_id"]
            logger.debug(f"Verified reset token for user {user_id}")
            return User.query.get(user_id)
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            return None

    @property
    def password(self):
        return self.password_hash  # Return the hashed password

    @password.setter
    def password(self, plain_text_password):
        """
        Set and hash the password.
        """
        self.password_hash = bcrypt.generate_password_hash(plain_text_password).decode("utf-8")

    def check_password(self, attempt_password):
        """
        Verify the provided password against the stored hash.
        """
        return bcrypt.check_password_hash(self.password_hash, attempt_password)

    def can_remove(self, item_obj):
        """
        Check if the user can remove the item.
        """
        return item_obj in self.items

    def update_info(self, update_form):
        """
        Update user information from a form.
        """
        self.name = update_form.name.data
        self.email_address = update_form.email_address.data
        self.mobile_number1 = update_form.mobile_number1.data
        self.mobile_number2 = update_form.mobile_number2.data
        self.state = update_form.state.data
        db.session.commit()  # Commit changes to the database

    def remove(self):
        """
        Remove the user from the database.
        """
        db.session.delete(self)
        db.session.commit()
        
    def change_password(self, new_password):
        """
        Change the user's password and commit the change to the database.
        """
        try:
            # Hash and update the password
            self.password = new_password
            db.session.commit()
            logger.debug(f"Password successfully changed for user {self.id}")
        except Exception as e:
            logger.error(f"Failed to change password for user {self.id}: {e}")
            db.session.rollback()  # Rollback in case of any error
            raise



class Item(db.Model):
    id = db.Column(db.Integer(), primary_key=True)  # Item ID
    name = db.Column(db.String(length=30), nullable=False)  # Item name
    price = db.Column(db.Integer(), nullable=False)  # Item price
    type = db.Column(db.String(length=12), nullable=False)  # Item type
    description = db.Column(db.String(length=1024), nullable=False)  # Item description
    location = db.Column(db.String(), nullable=False)  # Item location
    delivery = db.Column(db.String(), nullable=False)  # Delivery method
    owner = db.Column(db.Integer(), db.ForeignKey("user.id"))  # Owner reference
    images = db.relationship("Picture", backref="rel_item", lazy=True)  # Related images

    def __repr__(self):
        return f"Item(id={self.id}, name={self.name})"  # Represent item by its ID and name

    def buy(self, current_user):
        """
        Transfer ownership of the item to the buyer.
        """
        self.owner = current_user.id
        current_user.budget -= self.price  # Deduct price from buyer's budget
        db.session.commit()  # Commit changes to the database

    def remove(self):
        """
        Remove the item from the database.
        """
        db.session.delete(self)
        db.session.commit()

    def update_info(self, update_form):
        """
        Update item information from a form.
        """
        self.name = update_form.name.data
        self.price = update_form.price.data
        self.type = update_form.type.data
        self.description = update_form.description.data
        self.location = update_form.location.data
        db.session.commit()  # Commit changes to the database


class Picture(db.Model):
    id = db.Column(db.Integer(), primary_key=True)  # Picture ID
    image_name = db.Column(db.String())  # Image filename
    product = db.Column(db.Integer(), db.ForeignKey("item.id"))  # Related item reference