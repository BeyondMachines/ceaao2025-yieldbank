"""
Main Flask application for Banking Security Training
Initializes the Flask app with all necessary components
"""
from flask import Flask, request, session
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_wtf.csrf import CSRFProtect
from config import Config
from models import db, User
import os
import time
from dotenv import load_dotenv
from sqlalchemy.exc import SQLAlchemyError

from application.errors import register_error_handlers
from application.home import index, dashboard
from application.user import login, logout, profile, preferences, mfa_verify, mfa_setup
from application.api import api_stats, api_transactions
from application.transaction import transaction_detail, search, export_transactions, download_export_file, import_transactions, transaction_archive
from application.feedback import feedback_list, feedback_detail, submit_feedback, feedback_by_user
from application.ai import ai_loan_advisor, ai_transaction_research
# Load environment variables
load_dotenv()


def _initialize_schema_with_retry(app, attempts=10, delay_seconds=2):
    """
    Ensure core tables exist even when running plain `docker compose up`
    without an explicit migration/init step.
    """
    for attempt in range(1, attempts + 1):
        try:
            with app.app_context():
                db.create_all()
            app.logger.info("Database schema initialization check completed.")
            return
        except SQLAlchemyError as exc:
            if attempt == attempts:
                app.logger.error("Database schema initialization failed after retries: %s", exc)
                raise
            app.logger.warning(
                "Database not ready for schema init (attempt %s/%s): %s",
                attempt,
                attempts,
                exc,
            )
            time.sleep(delay_seconds)


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Cookie/session hardening.
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    local_test = os.getenv("LOCAL_TEST", "").lower() in {"1", "true", "yes"}
    secure_cookie_env = os.getenv("SESSION_COOKIE_SECURE")
    if secure_cookie_env is not None:
        app.config['SESSION_COOKIE_SECURE'] = secure_cookie_env.lower() in {"1", "true", "yes"}
    else:
        # Secure by default; explicit LOCAL_TEST allows local http labs to function.
        app.config['SESSION_COOKIE_SECURE'] = not local_test

    db.init_app(app)

    # Initialize database
    # db = SQLAlchemy(app)

    # Initialize Flask-Migrate
    migrate = Migrate(app, db)

    # Initialize extensions
    login_manager = LoginManager()
    login_manager.init_app(app)
    csrf = CSRFProtect()
    csrf.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        return User.query.get(int(user_id))

    # Template filters
    @app.template_filter('currency')
    def currency_format(value):
        """Format decimal values as currency"""
        if value is None:
            return "$0.00"
        return f"${value:,.2f}"

    @app.template_filter('datetime')
    def datetime_format(value, format='%Y-%m-%d %H:%M'):
        """Format datetime values"""
        if value is None:
            return ""
        return value.strftime(format)

    # Context processors for global template variables
    @app.context_processor
    def inject_config():
        """Make config available in all templates"""
        standard_prefs = session.get('standard_preferences', {}) or {}
        custom_config = session.get('custom_config', {}) or {}
        preferred_theme = standard_prefs.get('theme') or custom_config.get('theme') or 'auto'
        if preferred_theme not in {'light', 'dark', 'auto'}:
            preferred_theme = 'auto'
        return dict(
            BANK_NAME=app.config['BANK_NAME'],
            UI_THEME=preferred_theme
        )

    @app.after_request
    def set_security_headers(response):
        """Set baseline security headers for all responses."""
        response.headers.setdefault('X-Frame-Options', 'DENY')
        response.headers.setdefault('X-Content-Type-Options', 'nosniff')
        response.headers.setdefault('Referrer-Policy', 'strict-origin-when-cross-origin')
        response.headers.setdefault('Permissions-Policy', 'geolocation=(), microphone=(), camera=()')
        response.headers.setdefault('Content-Security-Policy', "default-src 'self'; script-src 'self' https://cdn.jsdelivr.net; style-src 'self' https://cdn.jsdelivr.net; font-src 'self' https://cdn.jsdelivr.net; connect-src 'self'; img-src 'self' data:; object-src 'none'; frame-ancestors 'none'; base-uri 'self'")
        if request.is_secure:
            response.headers.setdefault('Strict-Transport-Security', 'max-age=31536000; includeSubDomains')
        return response

    # First register the error handlers for nice error messages
    register_error_handlers(app)

    # Create home routes
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/dashboard', 'dashboard', dashboard)

    # Create user routes
    app.add_url_rule('/login', 'login', login, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', logout)
    app.add_url_rule('/profile', 'profile', profile)
    app.add_url_rule('/preferences', 'preferences', preferences, methods=['GET', 'POST'])
    app.add_url_rule('/mfa/verify', 'mfa_verify', mfa_verify, methods=['GET', 'POST'])
    app.add_url_rule('/mfa/setup', 'mfa_setup', mfa_setup, methods=['GET', 'POST'])

    # Create transaction routes
    app.add_url_rule('/transaction/<int:transaction_id>', 'transaction_detail', transaction_detail, methods=['GET', 'POST'])
    app.add_url_rule('/search', 'search', search, methods=['GET', 'POST'])
    
    app.add_url_rule('/export', 'export_transactions', export_transactions, methods=['GET', 'POST'])
    app.add_url_rule('/export/download', 'download_export_file', download_export_file, methods=['GET'])

    app.add_url_rule('/import', 'import_transactions', import_transactions, methods=['GET', 'POST'])
    app.add_url_rule('/archive', 'transaction_archive', transaction_archive, methods=['GET', 'POST'])

    # Create feedback routes
    app.add_url_rule('/feedback', 'feedback_list', feedback_list)
    app.add_url_rule('/feedback/<int:feedback_id>', 'feedback_detail', feedback_detail)
    app.add_url_rule('/feedback/submit', 'submit_feedback', submit_feedback, methods=['GET', 'POST'])
    app.add_url_rule('/feedback/user/<int:user_id>', 'feedback_by_user', feedback_by_user)


    # CREATE AI BANKING ROUTES (ADD THESE)
    app.add_url_rule('/ai/research', 'ai_transaction_research', ai_transaction_research, methods=['GET', 'POST'])
    app.add_url_rule('/ai/loan-advisor', 'ai_loan_advisor', ai_loan_advisor, methods=['GET', 'POST'])
    
    # Create api routes
    app.add_url_rule('/api/stats', 'api_stats', api_stats)
    app.add_url_rule('/api/transactions', 'api_transactions', api_transactions, methods=['POST'])

    auto_init_db = os.getenv("AUTO_INIT_DB", "true").lower() in {"1", "true", "yes"}
    if auto_init_db:
        _initialize_schema_with_retry(app)

    return app


# Now start the main application
if __name__ == '__main__':
    app = create_app()

    # Convert the DEBUG environment variable to a boolean
    # Flask's app.run(debug=...) expects a boolean value, but environment variables 
    # are typically strings. This code converts the DEBUG variable to a boolean.
    # It checks if the DEBUG variable is set to "true", "1", or "t" (case-insensitive).
    # If no DEBUG variable is set, it defaults to "False".
    if os.getenv("DB_HOST"):
        debuglevel = False
    else:
        debuglevel = True
    app.run(host='0.0.0.0', port=5000, debug=debuglevel)
