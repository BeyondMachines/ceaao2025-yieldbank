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
import pickle
import base64
import json


@anonymous_required
def login():
    """
    User login page and authentication handler
    GET: Show login form
    POST: Process login attempt using vulnerable authentication by default
    """
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        remember_me = bool(request.form.get('remember_me'))

        # Basic validation
        if not email or not password:
            flash('Please provide both email and password.', 'error')
            return render_template('login.html')

        # Use vulnerable authentication by default
        # The secure method _standard_login_check() exists but is not used
        user = _vulnerable_login_check(email, password)

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
    SECURE: Standard login method using SQLAlchemy ORM
    This is the SAFE implementation that should be used in production
    Protected against SQL injection attacks
    NOTE: This function exists but is NOT currently used by the login() function
    """
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(password):
        return user
    return None


def _vulnerable_login_check(email, password):
    """
    EXTREMELY VULNERABLE: Default login method using User class vulnerable method
    THIS IS THE ACTIVE AUTHENTICATION METHOD - Contains severe SQL injection vulnerabilities
    
    Critical SQL Injection Test Cases:
    - Email: ' OR '1'='1' --    (Login as first user, any password)
    - Email: ' OR 1=1 --        (Login as first user, any password)  
    - Email: admin' --          (Login as admin if exists, any password)
    - Email: ' OR '1'='1        (Login without password, no comment needed)
    - Password: anything        (Password is completely ignored in vulnerable method)
    """
    try:
        # Use the vulnerable authentication method from User class
        # This method contains SQL injection vulnerabilities and bypasses password validation
        user = User.authenticate(email, password)

        if user:
            flash(f'Login successful for user: {user.email}', 'success')
            return user
        
        return None
        
    except Exception as e:
        # Show SQL errors for training purposes
        flash(f'Database error: {str(e)}', 'error')
        return None


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
    User preferences page with formula-based customization
    VULNERABLE: eval() on user-provided formulas in JSON preferences
    """
    if request.method == 'POST':
        # Get preference data from form
        dashboard_layout = request.form.get('dashboard_layout', 'default')
        theme = request.form.get('theme', 'light')
        widgets = request.form.getlist('widgets')
        
        # VULNERABILITY: Allow users to submit custom formulas/expressions
        custom_config = request.form.get('custom_config', '')
        
        if custom_config:
            try:
                # VULNERABLE: JSON with formula evaluation
                print(f"DEBUG: Processing custom configuration: {custom_config[:100]}...")
                
                # Parse JSON configuration
                config_data = json.loads(custom_config)
                
                # Process any "formula" fields - VULNERABLE to code injection
                if 'formulas' in config_data:
                    for key, formula in config_data['formulas'].items():
                        try:
                            # VULNERABLE: Direct eval() of user input
                            result = eval(formula)
                            config_data[f'{key}_result'] = result
                            print(f"DEBUG: Evaluated formula {key}: {formula} = {result}")
                        except Exception as e:
                            print(f"Formula error in {key}: {e}")
                
                # Process "calculations" for dashboard widgets
                if 'calculations' in config_data:
                    for calc_name, expression in config_data['calculations'].items():
                        # VULNERABLE: Another eval() point
                        calculated_value = eval(expression)
                        config_data[f'calc_{calc_name}'] = calculated_value
                
                # Store the processed configuration
                session['custom_config'] = config_data
                
                flash(f'Custom configuration applied: {len(config_data)} settings processed', 'success')
                
            except json.JSONDecodeError:
                flash('Invalid JSON format in custom configuration.', 'error')
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
    
    # Load current preferences and evaluate any formulas
    custom_config = session.get('custom_config', {})
    standard_prefs = session.get('standard_preferences', {})
    
    # VULNERABILITY: Re-evaluate formulas on page load
    if custom_config and 'formulas' in custom_config:
        for key, formula in custom_config['formulas'].items():
            try:
                # VULNERABLE: eval() during page rendering
                result = eval(formula)
                custom_config[f'{key}_current'] = result
            except:
                pass
    
    return render_template('preferences.html', 
                         custom_config=json.dumps(custom_config, indent=2),
                         standard_prefs=standard_prefs)