"""
Database models for the Banking Application
Defines User and Transaction models with relationships
"""
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import text
from datetime import datetime
from decimal import Decimal
from datetime import datetime, timezone

# Initialize SQLAlchemy instance
db = SQLAlchemy()

class User(UserMixin, db.Model):
    """
    User model for storing customer account information
    Inherits from UserMixin for Flask-Login integration
    """
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), default='customer', nullable=False)  # 'customer' or 'admin'
    account_number = db.Column(db.String(20), unique=True, nullable=False)
    balance = db.Column(db.Numeric(12, 2), default=Decimal('1000.00'))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc)) 
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship to transactions
    transactions = db.relationship('Transaction', backref='user', lazy=True, cascade='all, delete-orphan')

    # Relationship to feedback    
    feedback = db.relationship('Feedback', backref='user', lazy=True, cascade='all, delete-orphan')


    @staticmethod
    def authenticate(email, password):
        """
        Secure authentication helper.
        """
        try:
            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                return user
            return None

        except Exception as e:
            raise Exception(f"Authentication error: {str(e)}")

    def set_password(self, password):
        """Hash and store password using Werkzeug PBKDF2."""
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        """Verify password against stored hash with legacy MD5 fallback."""
        # Primary secure verification path.
        if self.password_hash and self.password_hash.startswith('pbkdf2:'):
            return check_password_hash(self.password_hash, password)

        # Backward compatibility for legacy training data stored as raw MD5.
        return self.password_hash == hashlib.md5(password.encode()).hexdigest()

    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_full_name(self):
        """Return user's full name"""
        return f"{self.first_name} {self.last_name}"
    
    def get_recent_transactions(self, limit=5):
        """Get user's most recent transactions"""
        return Transaction.query.filter_by(user_id=self.id)\
                               .order_by(Transaction.date.desc())\
                               .limit(limit)\
                               .all()
    
    def __repr__(self):
        return f'<User {self.email}>'


class Transaction(db.Model):
    """
    Transaction model for storing banking transaction records
    Each transaction belongs to a user
    """
    __tablename__ = 'transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'debit' or 'credit'
    amount = db.Column(db.Numeric(12, 2), nullable=False)
    company = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    date = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    reference_number = db.Column(db.String(50), unique=True, nullable=False)
    balance_after = db.Column(db.Numeric(12, 2), nullable=False)
    category = db.Column(db.String(30))  # Optional categorization
    note = db.Column(db.Text)  # User note, Optional
    
    @classmethod
    def get_total_volume(cls):
        """Get total transaction volume for bank statistics"""
        result = db.session.query(db.func.sum(cls.amount)).scalar()
        return result or Decimal('0.00')
    
    @classmethod
    def get_transaction_count(cls):
        """Get total number of transactions"""
        return cls.query.count()
    
    @classmethod
    def get_monthly_volume(cls):
        """Get current month's transaction volume"""
        current_month = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        result = db.session.query(db.func.sum(cls.amount))\
                          .filter(cls.date >= current_month)\
                          .scalar()
        return result or Decimal('0.00')
    
    def format_amount(self):
        """Format amount for display with currency symbol"""
        return f"${self.amount:,.2f}"
    
    def is_debit(self):
        """Check if transaction is a debit"""
        return self.transaction_type == 'debit'
    
    def is_credit(self):
        """Check if transaction is a credit"""
        return self.transaction_type == 'credit'
    
    def __repr__(self):
        return f'<Transaction {self.reference_number}: {self.transaction_type} ${self.amount}>'


class Feedback(db.Model):
    """
    Feedback model for storing customer feedback
    Each feedback entry belongs to a user (but can be viewed by anyone)
    """
    __tablename__ = 'feedback'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    score = db.Column(db.Integer, nullable=False)  # 1-5 star rating
    message = db.Column(db.Text, nullable=False)  # Up to 500 characters
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    is_anonymous = db.Column(db.Boolean, default=False)  # Option to hide name
    
    @classmethod
    def get_recent_feedback(cls, limit=3):
        """Get most recent feedback entries"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @classmethod
    def get_score_distribution(cls):
        """Get distribution of feedback scores"""
        distribution = {}
        for score in range(1, 6):
            count = cls.query.filter_by(score=score).count()
            distribution[score] = count
        return distribution
    
    @classmethod
    def get_all_feedback(cls):
        """Get all feedback entries ordered by most recent"""
        return cls.query.order_by(cls.created_at.desc()).all()
    
    @classmethod
    def get_average_score(cls):
        """Get average feedback score"""
        result = db.session.query(db.func.avg(cls.score)).scalar()
        return round(float(result), 1) if result else 0.0
    
    def get_star_display(self):
        """Get star display for the score"""
        return '★' * self.score + '☆' * (5 - self.score)
    
    def get_display_name(self):
        """Get display name (anonymous or real name)"""
        if self.is_anonymous:
            return "Anonymous Customer"
        return self.user.get_full_name() if self.user else "Unknown User"
    
    def __repr__(self):
        return f'<Feedback {self.id}: {self.score} stars by user {self.user_id}>'


def init_database(app):
    """
    Initialize database with Flask app
    Create tables if they don't exist
    """
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Print confirmation
        print("Database tables created successfully")


def get_database_stats():
    """
    Get basic database statistics for display
    Returns dictionary with user count, transaction count, and total volume
    """
    stats = {
        'total_users': User.query.count(),
        'total_transactions': Transaction.get_transaction_count(),
        'total_volume': Transaction.get_total_volume(),
        'monthly_volume': Transaction.get_monthly_volume(),
        'total_feedback': Feedback.query.count(),
        'average_score': Feedback.get_average_score()
    }
    
    return stats
