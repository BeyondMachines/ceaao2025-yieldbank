#!/usr/bin/env python3
"""
Add More Transactions Tool
Simple utility to add additional transactions to existing users
Usage: python add_transactions.py [number_of_transactions_per_user]
"""

import sys
import random
from app import create_app
from models import User, Transaction

def add_more_transactions(transactions_per_user=None):
    """Add more transactions to all existing users"""
    
    # Get all non-admin users
    users = User.query.filter_by(role='customer', is_active=True).all()
    
    if not users:
        print("❌ No users found in database")
        return
    
    print(f"Found {len(users)} users")
    
    if transactions_per_user is None:
        transactions_per_user = random.randint(10, 30)
    
    print(f"Adding {transactions_per_user} transactions per user...\n")
    
    # Import the helper functions from populate script
    from populate_db import (
        create_transactions_for_user,
        used_reference_numbers
    )
    
    # Clear reference number tracker
    used_reference_numbers.clear()
    
    total_added = 0
    
    for i, user in enumerate(users, 1):
        # Generate transactions
        transactions = create_transactions_for_user(user, transactions_per_user)
        
        # Add to database
        db.session.add_all(transactions)
        total_added += len(transactions)
        
        print(f"✓ User {i}/{len(users)}: Added {len(transactions)} transactions for {user.email}")
    
    # Commit all at once
    db.session.commit()
    
    print(f"\n✅ Successfully added {total_added} total transactions!")
    print(f"📊 Average: {total_added / len(users):.1f} transactions per user")


if __name__ == '__main__':
    # Get transaction count from command line argument
    count = None
    if len(sys.argv) > 1:
        try:
            count = int(sys.argv[1])
            print(f"Will add {count} transactions per user\n")
        except ValueError:
            print("⚠️  Invalid number, using random count")
    
    # Create app context and run
    app = create_app()
    with app.app_context():
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        globals()['db'] = db
        
        add_more_transactions(count)