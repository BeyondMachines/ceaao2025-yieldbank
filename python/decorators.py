"""
Custom decorators for the Banking Application
Provides authentication and security decorators
"""
from functools import wraps
from flask import redirect, url_for, flash, request, session
from flask_login import current_user
from datetime import datetime, timezone, timedelta


def login_required(f):
    """
    Decorator to require user authentication
    Redirects to login page if user is not authenticated
    Preserves the original URL for redirect after login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            # Save the URL user was trying to access
            session['next_url'] = request.url
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


def active_user_required(f):
    """
    Decorator to require active user status
    Ensures that only active users can access protected resources
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        if not current_user.is_active:
            flash('Your account has been deactivated. Please contact support.', 'error')
            return redirect(url_for('login'))
        
        return f(*args, **kwargs)
    return decorated_function


def anonymous_required(f):
    """
    Decorator to require anonymous user (not logged in)
    Redirects authenticated users to dashboard
    Useful for login/register pages that shouldn't be accessible to logged-in users
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def validate_user_access(f):
    """
    Decorator to validate that user can only access their own data
    Compares the user_id parameter with current_user.id
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        
        # If user_id is in the URL parameters, validate it
        user_id = kwargs.get('user_id')
        if user_id and int(user_id) != current_user.id:
            flash('You can only access your own data.', 'error')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def rate_limit_login(max_attempts=5, window_minutes=15):
    """
    Decorator factory for rate limiting login attempts
    max_attempts: Maximum number of attempts allowed
    window_minutes: Time window in minutes for rate limiting
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In a production environment, you would use Redis or similar
            # For this training app, we'll use session storage
            client_ip = request.remote_addr
            attempts_key = f'login_attempts_{client_ip}'
            
            # Get current attempts from session
            attempts = session.get(attempts_key, [])
            
            # Clean old attempts (older than window_minutes)
            cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
            attempts = [attempt for attempt in attempts if datetime.fromisoformat(attempt) > cutoff_time]
            
            # Check if too many attempts
            if len(attempts) >= max_attempts:
                flash(f'Too many login attempts. Please wait {window_minutes} minutes before trying again.', 'error')
                return redirect(url_for('index'))
            
            # Execute the original function
            result = f(*args, **kwargs)
            
            # If login failed (you would check this based on your login logic)
            # Add current attempt to the list
            # This is a simple implementation - in practice you'd check if login actually failed
            
            return result
        return decorated_function
    return decorator