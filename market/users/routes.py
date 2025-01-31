import os
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from flask_login import current_user, login_required, login_user, logout_user
from wtforms.validators import ValidationError

from market import db
from market.items.forms import PostForm, RemoveForm, UpdateItem
from market.items.routes import add_item_picture, remove_item
from market.models import Item, Picture, User
from market.users.forms import (
    ChangePasswordForm,
    LoginForm,
    RegisterForm,
    RemoveForm,
    ResetForm,
    UpdateForm,
)
from market.users.utils import save_profile_picture, send_mail, send_verification_email, generate_password_reset_token, verify_password_reset_token

# Create a blueprint for user-related routes
users = Blueprint("users", __name__)

# Initialize Flask-Limiter for rate limiting
limiter = Limiter(
    key_func=get_remote_address,
    app=current_app,
    default_limits=["200 per day", "50 per hour"],  # Global rate limits
)

# Route for user registration
@users.route("/register", methods=["GET", "POST"])
@limiter.limit("10 per minute")  # Rate limit for registration
def register_page():
    form = RegisterForm()  # Initialize the registration form
    if form.validate_on_submit():
        # Store user data temporarily in the session
        session["new_user_data"] = {
            "name": form.name.data,
            "email_address": form.email_address.data,
            "mobile_number1": form.mobile_number1.data,
            "mobile_number2": form.mobile_number2.data,
            "password": form.password1.data,  # Store the plain password temporarily
        }

        # Send verification email to the user with the provided email address
        send_verification_email(form.email_address.data)

        flash("A verification email has been sent to your email address.", category="success")
        return redirect(url_for("users.verification_sent"))

    # Check and display form errors if any
    if form.errors:
        for error in form.errors.values():
            flash(error, category="danger")

    return render_template("register.html", form=form)  # Render the registration template


@users.route("/login", methods=["GET", "POST"])
@limiter.limit("10 per minute")  # Rate limit for login attempts
def login_page():
    change_password_form = ChangePasswordForm()  # Initialize change password form
    reset_form = ResetForm()  # Initialize reset form
    form = LoginForm()  # Initialize login form

    if request.method == "POST":
        # Handle login form submission
        if "login" in request.form and form.validate_on_submit():
            user = User.query.filter_by(email_address=form.email_address.data).first()

            # Check if user exists
            if user is None:
                flash("This username is not registered.", category="danger")
                return redirect(url_for("users.login_page"))

            # Validate password for the user
            if user.check_password(form.password.data):
                login_user(user)
                flash(f"Success! Welcome {user.name}", category="success")
                return redirect(url_for("items.categories_redirect"))  # Redirect to categories page
            else:
                flash("Invalid password!", category="danger")
                return redirect(url_for("users.login_page"))

    # Handle GET request to render the login page
    return render_template(
        "login.html",  # The HTML template for the login page
        form=form,  # Pass the login form
        change_password_form=change_password_form,  # Pass the change password form
        reset_form=reset_form,  # Pass the reset form
    )

# Route for user logout
@users.route("/logout")
def logout_page():
    # Logout the current user and display a message
    logout_user()
    flash("You have been logged out!", category="info")
    return redirect(url_for("items.categories_redirect"))  # Redirect to categories page

# Route for user profile
@users.route("/account", methods=["POST", "GET"])
@login_required  # Ensure the user is logged in before accessing the account page
def profile_page():
    post_form = PostForm()  # Initialize post form for posting new items
    remove_form = RemoveForm()  # Initialize remove form for deleting items
    update_form = UpdateForm(  # Pre-populate user details in the update form
        name=current_user.name,
        email_address=current_user.email_address,
        mobile_number1=current_user.mobile_number1,
        mobile_number2=current_user.mobile_number2,
        state=current_user.state,
    )

    update_item = UpdateItem()  # Form for updating item details
    owned_items = Item.query.filter_by(owner=current_user.id).all()  # Get all items owned by the current user

    # Feedback for empty results
    if not owned_items:
        flash("No items found.", category="info")

    if request.method == "POST":
        # Handle item removal process
        if "removed_item" in request.form and remove_form.validate_on_submit():
            removed_item = request.form.get("removed_item")
            item_obj = Item.query.filter_by(id=removed_item).first()
            if item_obj:
                if current_user.can_remove(item_obj):
                    item_obj.remove()  # Remove the item from the database
                    flash("Item removed successfully.", category="success")
                else:
                    flash("Only the item owner can delete it.", category="danger")
            else:
                flash("Item not found.", category="danger")
            return redirect(url_for("users.profile_page"))

        # Handle item posting process
        if "posted_item" in request.form and post_form.validate_on_submit():
            # Create a new item with the posted details
            new_item = Item(
                name=post_form.name.data,
                price=post_form.price.data,
                location=post_form.location.data,
                description=post_form.description.data,
                type=post_form.type.data,
                delivery=post_form.delivery.data,
                owner=current_user.id,  # Set the current user as the owner
            )
            db.session.add(new_item)  # Add the new item to the database
            db.session.commit()
            flash("Item added successfully.", category="success")
            try:
                # Handle file uploads for item pictures
                files = request.files.getlist("picture")
                for file in files:
                    image_name = add_item_picture(file, new_item.name, new_item.id)
                    new_pic = Picture(image_name=image_name, product=new_item.id)
                    db.session.add(new_pic)
                    db.session.commit()  # Commit new picture to the database
            except Exception as e:
                print(f"Error saving picture: {e}")

            return redirect(url_for("users.profile_page"))

        # Handle user profile update process
        if "updated_user" in request.form and update_form.validate_on_submit():
            if update_form.picture.data:  # Check if a new profile picture is uploaded
                if current_user.image_file:  # If the user has an existing profile picture
                    user_image = current_user.image_file
                    image_path = os.path.join(
                        current_app.root_path, "static", "profile_pics", user_image
                    )
                try:
                    # Remove the old profile picture from the file system
                    if os.path.exists(image_path):
                        os.remove(image_path)
                        print("File deleted successfully.")
                except Exception as e:
                    print(f"Error: {e}")

                # Save the new profile picture
                picture_file = save_profile_picture(update_form.picture.data)
                current_user.image_file = picture_file
            try:
                # Update user information in the database
                current_user.update_info(update_form)
                db.session.commit()  # Commit the updates to the database
                flash("Profile updated successfully.", category="success")
                return redirect(url_for("users.profile_page"))
            except ValidationError as e:
                flash(str(e), category="danger")  # Show specific validation errors
            except Exception as e:
                print(f"Unknown Error occurred: {str(e)}")

        # Handle item update process
        if "updated_item" in request.form and update_item.validate_on_submit():
            try:
                # Retrieve the current item from the form data
                current_item = request.form.get("updated_item")
                item_obj = Item.query.get(current_item)

                # Update item details with the new data
                item_obj.update_info(update_item)

                # Commit the updates to the database
                db.session.commit()
                flash("Item updated successfully.", category="success")

                # Handle file uploads for images associated with the item
                files = request.files.getlist("images")
                if files:  # Ensure that files are present
                    for file in files:
                        # Save the new image and associate it with the item
                        image_name = add_item_picture(file, item_obj.name, item_obj.id)
                        new_pic = Picture(image_name=image_name, product=item_obj.id)
                        db.session.add(new_pic)

                    # Commit the images to the database
                    db.session.commit()
                else:
                    flash("No images were uploaded.", category="warning")

                # Redirect to the profile page after the update
                return redirect(url_for("users.profile_page"))

            except ValidationError as e:
                # Catch form validation errors and display them
                flash(str(e), category="danger")
            except Exception as e:
                # Catch any other errors and display them
                print(f"Unknown Error occurred: {str(e)}")

    # Handle GET requests to render the account page
    return render_template(
        "account.html",
        owned_items=owned_items,  # Pass the user's owned items to the template
        post_form=post_form,  # Pass the post form to the template
        remove_form=remove_form,  # Pass the remove form to the template
        update_form=update_form,  # Pass the update form to the template
        update_item=update_item,  # Pass the update item form to the template
    )

# Route for owner profile
@users.route("/owner/<int:owner_id>", methods=["POST", "GET"])
def owner_profile(owner_id):
    owner = User.query.get(owner_id)  # Fetch the owner user by ID
    remove_form = RemoveForm()  # Initialize the form for removing an item
    update_item = UpdateItem()  # Initialize the form for updating an item
    owned_items = Item.query.filter_by(owner=owner_id).all()  # Fetch all items owned by the user

    # Feedback for empty results
    if not owned_items:
        flash("No items found for this user.", category="info")

    if request.method == "POST":
        # Check if the update item form has been submitted
        if "updated_item" in request.form and update_item.validate_on_submit():
            try:
                # Retrieve the current item ID from the form
                current_item_id = request.form.get("updated_item")
                item_obj = Item.query.get(current_item_id)  # Fetch the item by ID

                if item_obj is None:
                    flash("Item not found.", category="danger")
                    return redirect(url_for("users.owner_profile", owner_id=owner_id))

                # Update item details with the form data
                item_obj.update_info(update_item)

                # Handle file uploads for images
                files = request.files.getlist("images")
                if files:  # Ensure that files are present
                    for file in files:
                        # Save the new image and associate it with the item
                        image_name = add_item_picture(file, item_obj.name, item_obj.id)
                        new_pic = Picture(image_name=image_name, product=item_obj.id)
                        db.session.add(new_pic)

                # Commit the update to the database
                db.session.commit()
                flash("Item updated successfully.", category="success")
            except ValidationError as e:
                # Catch form validation errors
                flash(str(e), category="danger")
            except Exception as e:
                # Catch any other errors and flash them
                print(f"Unknown error occurred: {str(e)}")

            # Redirect to the profile page after the update
            return redirect(url_for("users.owner_profile", owner_id=owner_id))

    # For GET requests, render the owner profile page
    return render_template(
        "owner.html",
        owner=owner,
        owned_items=owned_items,
        update_item=update_item,
        remove_form=remove_form,
    )

# Route for email verification
from datetime import datetime, timedelta
from itsdangerous import URLSafeTimedSerializer

# Generate a secure token with expiration
def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="1030204050")

# Verify the token and check expiration
def verify_email_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(
            token, salt="1030204050", max_age=expiration
        )
        return email
    except Exception as e:
        print(f"Token verification failed: {e}")
        return None

@users.route("/verify_email/<token>")
def verify_email(token):
    
    #Route to verify the user's email using the token.

    try:
        # Verify the token
        email = User.verify_email_token(token)
        if not email:
            flash("The verification link is invalid or has expired.", "danger")
            current_app.logger.warning(f"Invalid or expired token: {token}")
            return redirect(url_for("users.register_page"))

        # Get the user data from the session
        new_user_data = session.get("new_user_data")
        if not new_user_data:
            flash("Something went wrong. Please register again.", "danger")
            current_app.logger.warning(f"No session data found for email: {email}")
            return redirect(url_for("users.register_page"))

        if new_user_data.get("email_address") != email:
            flash("Something went wrong. Please register again.", "danger")
            current_app.logger.warning(f"Session data mismatch for email: {email}")
            return redirect(url_for("users.register_page"))

        # Create the user in the database
        new_user = User(
            name=new_user_data["name"],
            email_address=new_user_data["email_address"],
            mobile_number1=new_user_data["mobile_number1"],
            mobile_number2=new_user_data["mobile_number2"],
            password=new_user_data["password"],  # Password is already hashed
            is_verified=True,  # Mark the user as verified
        )
        db.session.add(new_user)
        db.session.commit()

        # Clear the session data
        session.pop("new_user_data", None)

        flash("Email verified successfully! You can now log in.", "success")
        current_app.logger.info(f"User {email} successfully verified and created in the database.")
        return redirect(url_for("users.login_page"))

    except Exception as e:
        # Log unexpected errors and notify the user
        current_app.logger.error(f"An error occurred during email verification: {e}", exc_info=True)
        flash("An unexpected error occurred. Please try again later.", "danger")
        return redirect(url_for("users.register_page"))
    

# Route for removing a user
@users.route("/remove_user/<int:user_id>", methods=["POST"])
def remove_user(user_id):
    user = User.query.get(user_id)  # Fetch the user by ID

    if user:
        # Remove profile picture if it exists
        if user.image_file:
            user_image = user.image_file
            image_path = os.path.join(
                current_app.root_path, "static", "profile_pics", user_image
            )
            try:
                if os.path.exists(image_path):
                    os.remove(image_path)  # Remove image from the file system
                    print("File deleted successfully.")
            except Exception as e:
                print(f"Error: {e}")

        # Remove user's items if they have any
        if user.items:
            for item in user.items:
                try:
                    item_id = int(item.id)
                    remove_item(item_id)  # Remove each item
                except Exception as e:
                    print(f"Error removing item with ID {item.id}: {e}")
        user.remove()  # Remove the user from the database
        flash(f"User successfully removed.", "success")

    return redirect(url_for("users.register_page"))  # Redirect to the register page

# Route for resending verification email
@users.route("/resend_verification", methods=["GET", "POST"])
def resend_verification():
    """
    Route to resend the verification email to the user during the verification process.
    """
    # Ensure the user has pending registration data in the session
    new_user_data = session.get("new_user_data")

    if not new_user_data or "email_address" not in new_user_data:
        flash("No pending registration found. Please register first.", "danger")
        current_app.logger.warning("No new_user_data found in session or email_address missing.")
        return redirect(url_for("users.register_page"))  # Redirect to registration page

    email = new_user_data["email_address"]

    try:
        current_app.logger.debug(f"Resending verification email to: {email}")
        
        # Resend the verification email
        send_verification_email(email)
        session["email_sent"] = True  # Update the session flag
        flash("A new verification email has been sent to your email address!", "success")

    except Exception as e:
        # Log unexpected errors and notify the user
        current_app.logger.error(f"An error occurred while resending verification email: {e}", exc_info=True)
        flash("An unexpected error occurred. Please try again later.", "danger")

    return redirect(url_for("users.verification_sent"))  # Redirect to avoid form resubmission



@users.route("/verification-sent")
def verification_sent():
    """
    Display a confirmation page after the user has successfully requested an email verification.
    """
    # Check if the session has a flag for email sent
    if not session.get("email_sent"):
        flash("No verification email has been sent. Please register first.", "warning")
        return redirect(url_for("users.register_page"))

    # Show a confirmation message to the user
    return render_template("verification_sent.html")


@users.route("/reset_password", methods=["GET", "POST"])
@limiter.limit("5 per minute")  # Apply rate-limiting for this route
def reset_password():
    """
    Route for requesting and processing password reset with token validation.
    """
    token = request.args.get("token")  # Extract token from query parameters
    change_password_form = ChangePasswordForm()
    reset_form = ResetForm()

    if request.method == "POST":
        # Handle form submission for password reset (with token)
        if token:
            user = User.verify_reset_token(token)
            if not user:
                flash("The reset link is invalid or has expired.", "danger")
                return redirect(url_for("users.reset_password"))

            if change_password_form.validate_on_submit():
                # Hash the new password before saving it
                user.change_password(change_password_form.new_password.data)
                db.session.commit()
                flash("Your password has been successfully updated!", "success")
                return redirect(url_for("users.login_page"))
            else:
                # If form validation fails, re-render the template with errors
                return render_template("reset_password_with_token.html", change_password_form=change_password_form)
        
        # Handle reset request without token (send reset email)
        else:
            email = request.form.get("email_address")
            user = User.query.filter_by(email_address=email).first()
            if user:
                token = user.get_reset_token()
                send_mail(user)  # Call send_mail with the user object
                flash("Check your email for a password reset link!", category="success")
                return redirect(url_for("users.login_page"))
            else:
                flash("Email does not exist.", category="danger")
                return redirect(url_for("users.reset_password"))

    # Render appropriate template based on the presence of a token
    if token:
        return render_template("reset_password_with_token.html", change_password_form=change_password_form)
    else:
        return render_template("reset_password.html", reset_form=reset_form)