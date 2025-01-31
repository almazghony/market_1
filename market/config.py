import os
import logging
from logging.handlers import RotatingFileHandler

class Config:
    # Database URI - replace with your actual database URL
    SQLALCHEMY_DATABASE_URI = os.environ.get("SQLALCHEMY_DATABASE_URI", "sqlite:///market.db")

    # Secret Key - make sure to set a strong, random secret key
    SECRET_KEY = os.environ.get("SECRET_KEY", "1030204050")
    if not SECRET_KEY:
        raise ValueError("No SECRET_KEY set for Flask application. Please set it in your environment variables.")

    # Enable CSRF protection
    WTF_CSRF_ENABLED = True

    # Password salt for hashing, ideally set a random value
    SECURITY_PASSWORD_SALT = os.environ.get("SECURITY_PASSWORD_SALT", "1030204050")
    if not SECURITY_PASSWORD_SALT:
        raise ValueError("No SECURITY_PASSWORD_SALT set for Flask application. Please set it in your environment variables.")

    # Email server configurations
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")  # Use environment variable for flexibility
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 587))  # Port for TLS
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "True").lower() == "true"  # Enable TLS for email security
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME", "almazghony@gmail.com")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD", "nmacdhbwfkslwmpo")
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        raise ValueError("Email credentials (MAIL_USERNAME and MAIL_PASSWORD) are required. Please set them in your environment variables.")

    # Default sender info for emails
    MAIL_DEFAULT_SENDER = ("Market App", os.environ.get("MAIL_USERNAME"))

    # Security settings for cookies
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "False").lower() == "true"  # HTTPS-only cookies (disabled in development)
    SESSION_COOKIE_HTTPONLY = os.environ.get("SESSION_COOKIE_HTTPONLY", "True").lower() == "true"  # Restrict cookies to HTTP(S) access only
    SESSION_COOKIE_SAMESITE = os.environ.get("SESSION_COOKIE_SAMESITE", "Lax")  # Prevent CSRF attacks

    # Maximum upload size set to 16 MB
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 16 * 1024 * 1024))  # 16 MB limit by default

    # Logging configuration
    LOG_FILE = "market.log"
    LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
    LOG_LEVEL = logging.INFO

    # CSRF token expiry time (in seconds)
    WTF_CSRF_TIME_LIMIT = 7200  # 2 hours

    @staticmethod
    def init_app(app):
        # Configure logging
        handler = RotatingFileHandler(Config.LOG_FILE, maxBytes=1024 * 1024, backupCount=10)  # 1 MB per file, 10 backups
        handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
        app.logger.addHandler(handler)

        # Add console logging in development mode
        if app.debug:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(logging.Formatter(Config.LOG_FORMAT))
            app.logger.addHandler(console_handler)

        app.logger.setLevel(Config.LOG_LEVEL)

        # Log application startup
        app.logger.info("Market application started.")