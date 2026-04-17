"""
URL routes and view functions for the Banking Application
Handles all user interactions and page rendering
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import text
from models import db, User, Transaction
from decorators import login_required, anonymous_required, active_user_required
import json


@anonymous_required
def login():
    """
    User login page and authentication handler
    GET: Show login form
    POST: Process login attempt using secure authentication
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))

        # Basic validation
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('login.html')

        # Use secure authentication path
        user = _standard_login_check(email, password)

        if user:
            if not user.is_active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                return render_template('login.html')

            # Login successful
            login_user(user, remember=remember_me)

            # Redirect to intended page or dashboard
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid email or password.', 'error')

    return render_template('login.html')


def _standard_login_check(email, password):
    """
    Secure login method using SQLAlchemy ORM.
    Protected against SQL injection attacks.
    Also migrates legacy MD5 password hashes to PBKDF2 on successful login.
    """
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        # Transparent upgrade for legacy MD5 hashes.
        if user.password_hash and not user.password_hash.startswith('pbkdf2:'):
            user.set_password(password)
            db.session.commit()
        return user
    return None


def _validate_preferences_config(config_data):
    """
    Validate advanced preferences payload as data only.
    No executable expressions are allowed.
    """
    if not isinstance(config_data, dict):
        raise ValueError("Configuration must be a JSON object.")

    allowed_keys = {"dashboard_layout", "theme", "widgets", "limits", "notifications"}
    unknown = set(config_data.keys()) - allowed_keys
    if unknown:
        raise ValueError(f"Unsupported keys: {', '.join(sorted(unknown))}")

    if "dashboard_layout" in config_data and config_data["dashboard_layout"] not in {"default", "compact", "detailed", "custom"}:
        raise ValueError("Invalid dashboard_layout value.")

    if "theme" in config_data and config_data["theme"] not in {"light", "dark", "auto"}:
        raise ValueError("Invalid theme value.")

    if "widgets" in config_data:
        widgets = config_data["widgets"]
        if not isinstance(widgets, list):
            raise ValueError("widgets must be a list.")
        allowed_widgets = {"balance", "transactions", "charts"}
        if any(w not in allowed_widgets for w in widgets):
            raise ValueError("widgets contains unsupported values.")

    if "limits" in config_data:
        limits = config_data["limits"]
        if not isinstance(limits, dict):
            raise ValueError("limits must be an object.")
        for k, v in limits.items():
            if not isinstance(v, (int, float)):
                raise ValueError(f"limits.{k} must be numeric.")

    if "notifications" in config_data and not isinstance(config_data["notifications"], dict):
        raise ValueError("notifications must be an object.")


@login_required
def logout():
    """
    User logout handler
    Clears session and redirects to home page
    """
    logout_user()
    return redirect(url_for('index'))


@active_user_required
def profile():
    """
    User profile page showing account information
    Displays user details and account settings
    """
    # Get user's transaction statistics
    transaction_count = Transaction.query.filter_by(user_id=current_user.id).count()
    
    first_transaction = Transaction.query.filter_by(user_id=current_user.id)\
                                        .order_by(Transaction.date.asc())\
                                        .first()
    
    last_transaction = Transaction.query.filter_by(user_id=current_user.id)\
                                       .order_by(Transaction.date.desc())\
                                       .first()
    
    profile_stats = {
        'transaction_count': transaction_count,
        'first_transaction_date': first_transaction.date if first_transaction else None,
        'last_transaction_date': last_transaction.date if last_transaction else None,
        'account_age': (datetime.now(timezone.utc) - (current_user.created_at.replace(tzinfo=timezone.utc) if current_user.created_at.tzinfo is None else current_user.created_at)).days
    }
    
    return render_template('profile.html', profile_stats=profile_stats)



# @active_user_required
# def preferences():
#     """
#     User preferences page with serialized preference storage
#     VULNERABLE: Deserializes user preference objects from session
#     """
#     if request.method == 'POST':
#         # Get preference data from form
#         dashboard_layout = request.form.get('dashboard_layout', 'default')
#         theme = request.form.get('theme', 'light')
#         widgets = request.form.getlist('widgets')
        
#         # VULNERABILITY: Allow users to submit custom preference objects
#         custom_prefs = request.form.get('custom_preferences', '')
        
#         if custom_prefs:
#             try:
#                 # VULNERABLE: Deserialize user-provided preference data
#                 print(f"DEBUG: Processing custom preferences: {custom_prefs[:100]}...")
                
#                 # Decode and deserialize the custom preferences
#                 decoded_prefs = base64.b64decode(custom_prefs)
#                 preference_object = pickle.loads(decoded_prefs)
                
#                 # Store in session (vulnerable)
#                 session['user_preferences'] = custom_prefs
                
#                 flash(f'Custom preferences applied: {preference_object.get("message", "Applied successfully")}', 'success')
                
#             except Exception as e:
#                 flash(f'Error applying preferences: {str(e)}', 'error')
#         else:
#             # Standard preferences (safe)
#             prefs = {
#                 'dashboard_layout': dashboard_layout,
#                 'theme': theme,
#                 'widgets': widgets
#             }
#             session['standard_preferences'] = prefs
#             flash('Preferences updated successfully!', 'success')
        
#         return redirect(url_for('preferences'))
    
#     # Load current preferences
#     custom_prefs = session.get('user_preferences', '')
#     standard_prefs = session.get('standard_preferences', {})
    
#     # VULNERABILITY: Deserialize preferences on page load
#     if custom_prefs:
#         try:
#             decoded_prefs = base64.b64decode(custom_prefs)
#             preference_object = pickle.loads(decoded_prefs)
#             print(f"DEBUG: Loaded custom preferences: {preference_object}")
#         except:
#             pass
    
#     return render_template('preferences.html', 
#                          custom_prefs=custom_prefs,
#                          standard_prefs=standard_prefs)

@active_user_required
def preferences():
    """
    User preferences page with JSON-based customization.
    Stores validated data only.
    """
    if request.method == 'POST':
        # Get preference data from form
        dashboard_layout = request.form.get('dashboard_layout', 'default')
        theme = request.form.get('theme', 'light')
        widgets = request.form.getlist('widgets')
        
        custom_config = request.form.get('custom_config', '')
        
        if custom_config:
            try:
                config_data = json.loads(custom_config)
                _validate_preferences_config(config_data)

                # Store validated data only
                session['custom_config'] = config_data

                flash('Custom configuration applied successfully.', 'success')
            except json.JSONDecodeError:
                flash('Invalid JSON format in custom configuration.', 'error')
            except ValueError as e:
                flash(f'Invalid configuration: {str(e)}', 'error')
            except Exception as e:
                flash(f'Error processing configuration: {str(e)}', 'error')
        else:
            # Standard preferences (safe)
            prefs = {
                'dashboard_layout': dashboard_layout,
                'theme': theme,
                'widgets': widgets
            }
            session['standard_preferences'] = prefs
            flash('Preferences updated successfully!', 'success')
        
        return redirect(url_for('preferences'))
    
    # Load current preferences
    custom_config = session.get('custom_config', {})
    standard_prefs = session.get('standard_preferences', {})

    return render_template('preferences.html', 
                         custom_config=json.dumps(custom_config, indent=2),
                         standard_prefs=standard_prefs)
