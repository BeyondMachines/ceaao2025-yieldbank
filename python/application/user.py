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
import pyotp
import qrcode
import io
import base64


def _check_account_lockout(user):
    """Check if a user account is temporarily locked."""
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        remaining = int((user.locked_until - datetime.now(timezone.utc)).total_seconds() // 60)
        flash(f'Account locked. Please try again in {remaining} minute(s).', 'error')
        return True
    return False


def _record_failed_login(user):
    """Increment failed login attempts and lock account after 5 failures."""
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= 5:
        user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
        flash('Too many failed login attempts. Account locked for 15 minutes.', 'error')
    db.session.commit()


def _reset_failed_logins(user):
    """Clear failed login attempts on successful login."""
    if user.failed_login_attempts > 0 or user.locked_until is not None:
        user.failed_login_attempts = 0
        user.locked_until = None
        db.session.commit()


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

            if _check_account_lockout(user):
                return render_template('login.html')

            _reset_failed_logins(user)

            # MFA check: if enabled, store user id in session and redirect to MFA verification
            if user.mfa_enabled and user.mfa_secret:
                session['mfa_user_id'] = user.id
                session['mfa_remember'] = remember_me
                return redirect(url_for('mfa_verify'))

            # Login successful (no MFA)
            login_user(user, remember=remember_me)

            # Redirect to intended page or dashboard
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('dashboard'))
        else:
            # Check if user exists to track failed attempts
            existing_user = User.query.filter_by(email=email).first()
            if existing_user:
                _record_failed_login(existing_user)
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
            try:
                user.set_password(password)
                db.session.commit()
            except ValueError:
                # Legacy password does not meet new complexity rules;
                # keep the old hash and let the user change password later.
                db.session.rollback()
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


@anonymous_required
def mfa_verify():
    """
    MFA verification page
    POST: Verify TOTP code and complete login
    """
    user_id = session.get('mfa_user_id')
    if not user_id:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user:
        session.pop('mfa_user_id', None)
        session.pop('mfa_remember', None)
        flash('Invalid session. Please log in again.', 'error')
        return redirect(url_for('login'))

    if request.method == 'POST':
        code = request.form.get('mfa_code', '').strip()
        if not code:
            flash('Please enter the authentication code.', 'error')
            return render_template('mfa_verify.html')

        totp = pyotp.TOTP(user.mfa_secret)
        if totp.verify(code, valid_window=1):
            # MFA verified — complete login
            remember_me = session.pop('mfa_remember', False)
            session.pop('mfa_user_id', None)
            login_user(user, remember=remember_me)
            flash('Login successful! MFA verified.', 'success')
            next_url = session.pop('next_url', None)
            return redirect(next_url or url_for('dashboard'))
        else:
            flash('Invalid authentication code. Please try again.', 'error')

    return render_template('mfa_verify.html')


@active_user_required
def mfa_setup():
    """
    MFA setup page for logged-in users
    GET: Show QR code and setup instructions
    POST: Enable or disable MFA
    """
    user = current_user

    if request.method == 'POST':
        action = request.form.get('action', '')

        if action == 'disable':
            user.mfa_enabled = False
            user.mfa_secret = None
            db.session.commit()
            flash('MFA has been disabled.', 'success')
            return redirect(url_for('mfa_setup'))

        if action == 'enable':
            verify_code = request.form.get('verify_code', '').strip()
            if not user.mfa_secret:
                flash('MFA secret not found. Please reload the page.', 'error')
                return redirect(url_for('mfa_setup'))

            totp = pyotp.TOTP(user.mfa_secret)
            if totp.verify(verify_code, valid_window=1):
                user.mfa_enabled = True
                db.session.commit()
                flash('MFA has been enabled successfully!', 'success')
                return redirect(url_for('mfa_setup'))
            else:
                flash('Invalid verification code. MFA was not enabled.', 'error')
                return redirect(url_for('mfa_setup'))

    # Generate secret if not present
    if not user.mfa_secret:
        user.mfa_secret = pyotp.random_base32()
        db.session.commit()

    # Generate QR code
    totp = pyotp.TOTP(user.mfa_secret)
    provisioning_uri = totp.provisioning_uri(
        name=user.email,
        issuer_name="YieldBank"
    )

    qr = qrcode.make(provisioning_uri)
    buf = io.BytesIO()
    qr.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')

    return render_template(
        'mfa_setup.html',
        qr_code=qr_base64,
        secret=user.mfa_secret,
        mfa_enabled=user.mfa_enabled
    )


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
