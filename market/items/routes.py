import io
import os
import secrets
import shutil
from PIL import Image, ImageOps  # For image processing
from flask import (
    Blueprint,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    current_app,
)
from werkzeug.utils import secure_filename  # For secure filenames
from flask_limiter import Limiter  # For rate limiting
from flask_limiter.util import get_remote_address  # For rate limiting
from market import db  # Database object
from market.items.forms import PostForm  # Form for posting items
from market.models import Item, Picture  # Database models

# Create a blueprint for item-related routes
items = Blueprint("items", __name__)

# Initialize Flask-Limiter for rate limiting
limiter = Limiter(
    get_remote_address,
    app=current_app,
    default_limits=["200 per day", "50 per hour"],
)

# Allowed file extensions for image uploads
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


# Helper function to check if a file has an allowed extension
def allowed_file(filename):
    return os.path.splitext(filename)[1].lower() in ALLOWED_EXTENSIONS


# Route to redirect to the market page without a category selection
@items.route("/categories", methods=["GET"])
def categories_redirect():
    return redirect(url_for("items.market_page"))


# Main route for displaying the market page with item filters and price sorting
@items.route("/market", methods=["GET"])
@limiter.limit("10 per minute")  # Rate limit for the market page
def market_page():
    post_form = PostForm()  # Initialize the PostForm for adding new items

    # Get filter parameters from the query string
    category = request.args.get("category")
    price_range = request.args.get("priceRange")
    location = request.args.get("location")
    delivery = request.args.get("delivery")
    sort_by_price = request.args.get("sort", "asc")  # Default to ascending

    # If no category is selected, render the default category view
    if not category:
        return render_template("market.html", type=None)

    # Base query filtered by the selected category
    query = Item.query.filter_by(type=category)

    # Apply price filtering based on selected price range
    if price_range:
        if price_range == "1":
            query = query.filter(Item.price < 50)
        elif price_range == "2":
            query = query.filter(Item.price.between(50, 100))
        elif price_range == "3":
            query = query.filter(Item.price > 100)

    # Apply location filtering based on the entered location
    if location:
        query = query.filter(Item.location.ilike(f"%{location}%"))

    # Apply delivery filtering if the option is selected
    if delivery:
        query = query.filter(Item.delivery == delivery)

    # Apply sorting by price (ascending or descending)
    if sort_by_price == "asc":
        query = query.order_by(Item.price.asc())
    elif sort_by_price == "desc":
        query = query.order_by(Item.price.desc())

    # Pagination
    page = request.args.get("page", 1, type=int)  # Get the current page number
    per_page = 10  # Number of items per page
    market_items = query.paginate(page=page, per_page=per_page)

    # Feedback for empty results
    if not market_items.items:
        flash("No items found matching your filters.", "info")

    # Render the market template with the filtered and sorted items and the form
    return render_template(
        "market.html",
        market_items=market_items,
        post_form=post_form,
        type=category,
    )


# Function to save item pictures with resizing and compression
def add_item_picture(form_picture, item_name, item_id):
    # Validate file extension
    if not allowed_file(form_picture.filename):
        raise ValueError("Invalid file type. Only JPG, JPEG, and PNG files are allowed.")

    # Generate a secure filename
    random_hex = secrets.token_hex(8)
    _, f_extension = os.path.splitext(form_picture.filename)
    picture_fn = secure_filename(random_hex + f_extension)

    # Define the path to save the picture
    directory_path = os.path.join(current_app.root_path, "static", "image_pics", str(item_id))
    os.makedirs(directory_path, exist_ok=True)  # Create directory if it doesn't exist
    picture_path = os.path.join(directory_path, picture_fn)

    # Open and process the image
    with Image.open(form_picture) as img:
        img = ImageOps.exif_transpose(img)  # Correct orientation
        img.thumbnail((800, 800))  # Resize to 800x800 pixels
        img.save(picture_path, "JPEG", quality=85)  # Save with compression

    return picture_fn  # Return the generated picture filename


# Route to remove an image from the database and filesystem
@items.route("/remove_image/<int:image_id>", methods=["POST"])
@limiter.limit("5 per minute")  # Rate limit for image deletion
def remove_image(image_id):
    # Fetch the image record from the database using its ID
    picture = Picture.query.get_or_404(image_id)

    # Get the image file name and directory path
    image_name = picture.image_name
    product_id = str(picture.product)
    directory_path = os.path.join(current_app.root_path, "static", "image_pics", product_id)
    file_path = os.path.join(directory_path, image_name)

    # Try to remove the file from the filesystem
    try:
        if os.path.exists(file_path):
            os.remove(file_path)  # Delete the file if it exists
            flash("File deleted successfully.", "success")
        else:
            flash(f"File does not exist: {file_path}", "warning")
    except Exception as e:
        flash(f"Error occurred while deleting file: {e}", "error")

    # Try to remove the image record from the database
    try:
        db.session.delete(picture)  # Delete the image record from the database
        db.session.commit()  # Commit the transaction
        flash("Image removed successfully!", "success")
    except Exception as e:
        flash(f"Error occurred while removing image from database: {e}", "error")
        db.session.rollback()  # Rollback transaction in case of error

    # Redirect back to the referring page or a default route
    return redirect(request.referrer or url_for("items.market_page"))


# Route to remove an item from the database and filesystem
@items.route("/remove_item/<int:item_id>", methods=["POST"])
@limiter.limit("5 per minute")  # Rate limit for item deletion
def remove_item(item_id):
    # Fetch the item from the database using item_id
    product = Item.query.get_or_404(item_id)

    try:
        # Define the path to the item's image directory
        directory_path = os.path.join(current_app.root_path, "static", "image_pics", str(item_id))

        # Check if the directory exists and delete it
        if os.path.exists(directory_path):
            shutil.rmtree(directory_path)  # Remove the entire directory and its contents

        # Remove the item from the database
        db.session.delete(product)  # Delete the item from the database
        db.session.commit()  # Commit the transaction
        flash(f"Item successfully removed.", "success")

    except Exception as e:
        # Handle exceptions that occur during the removal process
        db.session.rollback()  # Rollback the transaction in case of error
        flash(f"An error occurred while removing the item: {str(e)}", "danger")

    # Redirect back to the referring page or a default route
    return redirect(request.referrer or url_for("items.market_page"))