from flask import Flask
from flask_bcrypt import Bcrypt
from flask_caching import Cache
from flask_login import LoginManager
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import logging
from logging.handlers import RotatingFileHandler

from market.config import Config

# Initialize extensions
mail = Mail()  # For sending emails
db = SQLAlchemy()  # For database interactions
bcrypt = Bcrypt()  # For password hashing
cache = Cache()  # For caching

# Set up login manager for user authentication
login_manager = LoginManager()
login_manager.login_view = "users.login_page"  # Redirect to login page if not logged in
login_manager.login_message_category = "info"  # Message category for login alerts
login_manager.login_message = "Please Log in first"  # Message displayed when login is required


def create_app(config_class=Config):
    """
    Application factory function to create and configure the Flask app.
    """
    app = Flask(__name__)  # Create Flask application instance
    app.config.from_object(config_class)  # Load configuration from the specified class

    # Initialize logging
    configure_logging(app)

    app.app_context().push()  # Push application context

    # Initialize extensions with the app
    initialize_extensions(app)

    # Register blueprints
    register_blueprints(app)

    return app  # Return the configured app instance


def configure_logging(app):
    """
    Configure logging for the application.
    """
    if not app.debug:
        # Set up a rotating file handler for logging
        handler = RotatingFileHandler("market.log", maxBytes=1024 * 1024, backupCount=10)  # 1 MB per file, 10 backups
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        app.logger.addHandler(handler)
        app.logger.setLevel(logging.INFO)
        app.logger.info("Market application started.")


def initialize_extensions(app):
    """
    Initialize Flask extensions with the app.
    """
    mail.init_app(app)
    db.init_app(app)
    bcrypt.init_app(app)
    login_manager.init_app(app)
    cache.init_app(app)  # Initialize caching


def register_blueprints(app):
    """
    Register blueprints for modular routing.
    """
    from market.errors.handlers import errors
    from market.items.routes import items
    from market.main.routes import main
    from market.users.routes import users

    app.register_blueprint(users)  # User-related routes
    app.register_blueprint(items)  # Item-related routes
    app.register_blueprint(main)  # Main application routes
    app.register_blueprint(errors)  # Error handling routes