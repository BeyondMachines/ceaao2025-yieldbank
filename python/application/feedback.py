"""
Feedback routes for the Banking Application
Handles customer feedback functionality with intentional XSS vulnerabilities for training
"""
from flask import render_template, request, redirect, url_for, flash
from flask_login import current_user
from models import db, Feedback, User
from decorators import active_user_required
import html
import re


def feedback_list():
    """
    Public feedback list page - shows all feedback entries
    Anyone can view this page (no authentication required)
    """
    # Get all feedback entries
    feedback_entries = Feedback.get_all_feedback()
    
    # Get score distribution for statistics
    score_distribution = Feedback.get_score_distribution()
    average_score = Feedback.get_average_score()
    total_feedback = len(feedback_entries)
    
    return render_template('feedback_list.html', 
                         feedback_entries=feedback_entries,
                         score_distribution=score_distribution,
                         average_score=average_score,
                         total_feedback=total_feedback)


def feedback_detail(feedback_id):
    """
    Public feedback detail page - shows individual feedback entry
    Anyone can view this page (no authentication required)
    VULNERABLE: Displays user content without escaping (XSS vulnerability)
    """
    feedback = Feedback.query.get_or_404(feedback_id)
    
    # Get other feedback from the same user (if not anonymous)
    other_feedback = []
    if not feedback.is_anonymous and feedback.user:
        other_feedback = Feedback.query.filter(
            Feedback.user_id == feedback.user_id,
            Feedback.id != feedback.id
        ).order_by(Feedback.created_at.desc()).limit(5).all()
    
    return render_template('feedback_detail.html', 
                         feedback=feedback,
                         other_feedback=other_feedback)


@active_user_required
def submit_feedback():
    """
    Feedback submission form for authenticated users
    GET: Show feedback form
    POST: Process feedback submission
    VULNERABLE: Stores user input without sanitization (XSS vulnerability)
    """
    if request.method == 'POST':
        score = request.form.get('score')
        message = request.form.get('message', '').strip()
        is_anonymous = bool(request.form.get('is_anonymous'))
        
        # Basic validation
        if not score or not message:
            flash('Please provide both a rating and feedback message.', 'error')
            return render_template('submit_feedback.html')
        
        try:
            score = int(score)
            if score < 1 or score > 5:
                flash('Rating must be between 1 and 5 stars.', 'error')
                return render_template('submit_feedback.html')
        except ValueError:
            flash('Invalid rating value.', 'error')
            return render_template('submit_feedback.html')
        
        # Check message length
        if len(message) > 500:
            flash('Feedback message must be 500 characters or less.', 'error')
            return render_template('submit_feedback.html')

        feedback = Feedback(
            user_id=current_user.id,
            score=score,
            message=message,  # VULNERABLE: No HTML escaping or sanitization
            is_anonymous=is_anonymous
        )
        try:
            db.session.add(feedback)
            db.session.commit()
            
            flash('Thank you for your feedback! Your input helps us improve our services.', 'success')
            return redirect(url_for('feedback_list'))
            
        except Exception as e:
            db.session.rollback()
            flash('An error occurred while submitting your feedback. Please try again.', 'error')
            print(f"Feedback submission error: {e}")
    
    return render_template('submit_feedback.html')



# Additional vulnerable helper functions for the feedback system


def feedback_by_user(user_id):
    """
    Show all feedback by a specific user
    VULNERABLE: Displays all user feedback without proper authorization
    this is an IDOR, just for fun.
    """
    user = User.query.get_or_404(user_id)
    
    # Get all feedback from this user (including non-anonymous)
    feedback_entries = Feedback.query.filter_by(user_id=user_id)\
                                    .order_by(Feedback.created_at.desc())\
                                    .all()
    
    return render_template('feedback_by_user.html',
                         user=user,
                         feedback_entries=feedback_entries)

