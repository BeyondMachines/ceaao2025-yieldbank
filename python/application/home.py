from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, and_
from models import db, User, Transaction, get_database_stats, Feedback
from decorators import login_required, anonymous_required, active_user_required
import threading
import random
import time


def index():
    """
    Home page with bank statistics and login form
    Shows basic stats pulled from database
    """
    # Get database statistics for display
    try:
        stats = get_database_stats()
    except Exception as e:
        print(f"Database not ready: {e}")
        stats = {
            "total_users": 0,
            "total_transactions": 0,
            "total_volume": 0,
            "monthly_volume": 0,
            "total_feedback": 0,
            "average_score": 0.0
        }
    
    return render_template('index.html', stats=stats)


@active_user_required
def dashboard():
    """
    User dashboard showing account overview and recent transactions
    Displays user's account information and transaction history
    """
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Get user's transactions with pagination
    transactions = Transaction.query.filter_by(user_id=current_user.id)\
                                  .order_by(Transaction.date.desc())\
                                  .paginate(
                                      page=page,
                                      per_page=per_page,
                                      error_out=False
                                  )
    
    # Calculate account summary
    total_credits = db.session.query(db.func.sum(Transaction.amount))\
                             .filter_by(user_id=current_user.id, transaction_type='credit')\
                             .scalar() or 0
    
    total_debits = db.session.query(db.func.sum(Transaction.amount))\
                            .filter_by(user_id=current_user.id, transaction_type='debit')\
                            .scalar() or 0
    
    # Get recent activity (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    recent_activity_count = Transaction.query.filter_by(user_id=current_user.id)\
                                           .filter(Transaction.date >= thirty_days_ago)\
                                           .count()
    
    # Get score distribution for statistics
    average_score = Feedback.get_average_score()
    
    summary = {
        'total_credits': total_credits,
        'total_debits': total_debits,
        'recent_activity_count': recent_activity_count,
        'average_score': average_score
    }
    
    return render_template('dashboard.html', 
                        transactions=transactions, 
                        summary=summary)

