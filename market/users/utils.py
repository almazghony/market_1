import io
import os
import secrets
from PIL import Image, ExifTags
from flask import current_app, flash, url_for
from flask_mail import Message
from market import mail
from market.models import User
from itsdangerous import URLSafeTimedSerializer


# Function to send password reset email
def send_mail(user):
    token = user.get_reset_token()  # Generate a token for password reset
    msg = Message(
        "Password Reset Request",
        recipients=[user.email_address],
        sender="almazghony@gmail.com",  # Sender email address
    )

    # HTML formatted email body
    msg.html = f"""
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                background-color: #f8f9fa;
                color: #343a40;
                padding: 20px;
                border-radius: 5px;
                border: 1px solid #dee2e6;
            }}
            h2 {{
                color: #ff0000; /* Red color for headings */
            }}
            p {{
                font-size: 16px;
                line-height: 1.5;
            }}
            a {{
                color: #ff0000; /* Red color for links */
                text-decoration: none;
                font-weight: bold;
            }}
            a:hover {{
                text-decoration: underline;
            }}
            .footer {{
                margin-top: 20px;
                font-size: 12px;
                color: #6c757d;
            }}
        </style>
    </head>
    <body>
        <h2>Password Reset Request</h2>
        <p>
            To reset your password, please click the following link:
        </p>
        <p>
            <a href="{url_for('users.reset_password', token=token, _external=True)}">
                Reset Your Password
            </a>
        </p>
        <p>
            If you did not make this request, please ignore this email.
        </p>
        <div class="footer">
            <p>&copy; '2024' Flask Market. All Rights Reserved.</p>
        </div>
    </body>
    </html>
    """

    try:
        mail.send(msg)  # Send the email
    except Exception as e:
        print(f"Failed to send email: {e}")


# Function to save the profile picture
def save_profile_picture(form_picture):
    try:
        # Generate a random hex for the picture filename
        random_hex = secrets.token_hex(8)
        _, f_extension = os.path.splitext(form_picture.filename)
        picture_fn = random_hex + f_extension
        picture_path = os.path.join(
            current_app.root_path, "static", "profile_pics", picture_fn
        )

        # Open the image using PIL
        i = Image.open(form_picture)

        # Handle image orientation using EXIF data
        try:
            for orientation in ExifTags.TAGS.keys():
                if ExifTags.TAGS[orientation] == "Orientation":
                    break
            exif = i._getexif()

            # Check and adjust image orientation if needed
            if exif is not None and orientation in exif:
                if exif[orientation] == 3:
                    i = i.rotate(180, expand=True)
                elif exif[orientation] == 6:
                    i = i.rotate(270, expand=True)
                elif exif[orientation] == 8:
                    i = i.rotate(90, expand=True)
        except Exception as e:
            print(f"Could not process EXIF data: {e}")

        # Resize the image to a smaller size for the profile picture
        output_size = (500, 500)
        i.thumbnail(output_size)

        # Save the image with compression to reduce file size
        with io.BytesIO() as output:
            i.save(output, format="JPEG", quality=85)  # Adjust quality as needed
            output.seek(0)
            i.save(picture_path, "JPEG")

        return picture_fn  # Return the filename of the saved picture
    except Exception as e:
        print(f"Error saving profile picture: {e}")
        return None

# Function to send verification email
from flask import url_for, flash
from flask_mail import Message
from market import mail

def send_verification_email(email):
    """
    Sends a verification email to the user with a link to verify their email address.
    """
    # Generate a verification token using the User model's method
    token = User.generate_verification_token(email)

    # Create the verification link
    verification_link = url_for("users.verify_email", token=token, _external=True)

    # Create the email message
    msg = Message(
        "Verify Your Email",
        recipients=[email],
        sender=current_app.config["MAIL_DEFAULT_SENDER"],  # Use the configured sender
    )

    # HTML formatted email body for verification
    msg.html = f"""
    <html>
        <body style="font-family: Arial, sans-serif; color: #212121;">
            <h2 style="color: #212121;">Verify Your Email</h2>
            <p>To verify your email, please click the following link:</p>
            <p>
                <a href="{verification_link}" style="color: #0066cc; text-decoration: none; font-weight: bold;">
                    Verify Email
                </a>
            </p>
            <p>If you did not register, please ignore this email.</p>
            <p>Thank you!</p>
        </body>
    </html>
    """

    try:
        # Send the email
        mail.send(msg)
        flash("A verification email has been sent to your email address.", "success")
    except Exception as e:
        # Log the error and notify the user
        current_app.logger.error(f"Failed to send verification email: {e}")
        flash("Failed to send verification email. Please try again later.", "danger")

def generate_password_reset_token(email):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    return serializer.dumps(email, salt="password_reset_salt")

def verify_password_reset_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
    try:
        email = serializer.loads(token, salt="password_reset_salt", max_age=expiration)
        return email
    except Exception:
        return None
