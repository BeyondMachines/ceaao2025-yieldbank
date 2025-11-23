"""
Populate historical transaction tables with data for 2020-2021
Reuses existing transaction creation logic from populate_db.py
"""
import random
import string
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker
from sqlalchemy import text
from app import create_app
from populate_db import (
    SAMPLE_COMPANIES, 
    TRANSACTION_CATEGORIES,
    generate_reference_number,
    used_reference_numbers
)

# Initialize Faker
fake = Faker()

def get_date_range_for_month(year, month):
    """
    Get the start and end dates for a specific month
    """
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1) - timedelta(days=1)
    
    return start_date, end_date

def create_historical_transaction_data(user, year, month, transaction_count=None):
    """
    Create historical transaction data for a specific user and month
    Reuses the same logic as populate_db.py but for specific time periods
    """
    if user.role == 'admin':
        return []
    
    if transaction_count is None:
        # Fewer transactions in historical data (20-40 per month)
        transaction_count = random.randint(20, 40)
    
    start_date, end_date = get_date_range_for_month(year, month)
    
    # Generate transaction dates within the month
    transaction_dates = []
    for _ in range(transaction_count):
        random_date = fake.date_time_between(start_date=start_date, end_date=end_date)
        transaction_dates.append(random_date)
    
    # Sort dates chronologically
    transaction_dates.sort()
    
    transactions = []
    
    # Start with a reasonable balance for historical data
    # Simulate balance at the beginning of the month
    balance_variance = random.uniform(0.8, 1.2)  # +/- 20% variance
    current_balance = Decimal(str(round(float(user.balance) * balance_variance, 2)))
    
    for transaction_date in transaction_dates:
        # 70% debit, 30% credit (same as current logic)
        is_credit = random.random() < 0.30
        transaction_type = 'credit' if is_credit else 'debit'
        
        # Generate amount
        if is_credit:
            amount = Decimal(str(round(random.uniform(50.00, 1500.00), 2)))
        else:
            amount = Decimal(str(round(random.uniform(5.00, 500.00), 2)))
        
        # Update balance
        if is_credit:
            current_balance += amount
        else:
            current_balance -= amount
        
        current_balance = Decimal(str(round(float(current_balance), 2)))
        
        # Generate company and category
        company = random.choice(SAMPLE_COMPANIES)
        category = random.choice(TRANSACTION_CATEGORIES)
        
        # Generate description
        descriptions = [
            f"Purchase at {company}",
            f"Payment to {company}",
            f"Online order from {company}",
            f"Service fee - {company}",
            f"Subscription - {company}",
            f"Refund from {company}" if is_credit else f"Bill payment - {company}"
        ]
        description = random.choice(descriptions)
        
        # Generate unique reference number
        reference_number = generate_reference_number()
        
        # Create transaction data dictionary
        transaction_data = {
            'user_id': user.id,
            'transaction_type': transaction_type,
            'amount': float(amount),
            'company': company,
            'description': description,
            'date': transaction_date,
            'reference_number': reference_number,
            'balance_after': float(current_balance),
            'category': category
        }
        
        transactions.append(transaction_data)
    
    return transactions

def populate_historical_table(year, month, users, db):
    """
    Populate a specific historical table with transaction data
    """
    table_name = f"transactions_{year}{month:02d}"
    
    print(f"  📅 Populating {table_name}...")
    
    all_transactions = []
    
    # Create transactions for each user
    for user in users:
        if user.role == 'admin':
            continue
            
        user_transactions = create_historical_transaction_data(user, year, month)
        all_transactions.extend(user_transactions)
    
    if not all_transactions:
        print(f"    ⚠️  No transactions generated for {table_name}")
        return 0
    
    # Insert transactions using raw SQL for efficiency
    insert_query = f"""
        INSERT INTO {table_name} 
        (user_id, transaction_type, amount, company, description, date, 
         reference_number, balance_after, category)
        VALUES 
        (:user_id, :transaction_type, :amount, :company, :description, 
         :date, :reference_number, :balance_after, :category)
    """
    
    try:
        db.session.execute(text(insert_query), all_transactions)
        db.session.commit()
        print(f"    ✓ Inserted {len(all_transactions)} transactions into {table_name}")
        return len(all_transactions)
    except Exception as e:
        db.session.rollback()
        print(f"    ❌ Error populating {table_name}: {e}")
        return 0

def populate_all_historical_tables(db=None, User=None):
    """
    Populate all historical tables with transaction data
    """
    if db is None or User is None:
        # If called without parameters, set up db and User locally
        app = create_app()
        with app.app_context():
            from flask import current_app
            from models import User as UserModel
            db = current_app.extensions['sqlalchemy']
            User = UserModel
            return _populate_all_historical_tables_impl(db, User)
    else:
        return _populate_all_historical_tables_impl(db, User)

def _populate_all_historical_tables_impl(db, User):
    """
    Implementation of populate_all_historical_tables
    """
    print("=" * 60)
    print("Populating Historical Transaction Tables")
    print("=" * 60)
    
    # Get all users
    users = db.session.query(User).all()
    if not users:
        print("❌ No users found. Run populate_db.py first!")
        return
    
    print(f"📊 Found {len(users)} users")
    
    total_transactions = 0
    
    # Populate each year and month
    for year in [2020, 2021]:
        print(f"\n📅 Processing year {year}...")
        
        for month in range(1, 13):
            month_name = datetime(year, month, 1).strftime("%B")
            print(f"  📅 {month_name} {year}")
            
            transaction_count = populate_historical_table(year, month, users, db)
            total_transactions += transaction_count
    
    print(f"\n✅ Historical data population complete!")
    print(f"   Total historical transactions created: {total_transactions:,}")
    print("=" * 60)

def check_historical_tables_exist(db):
    """
    Check if historical tables exist in the database
    """
    try:
        # Check if at least one historical table exists
        result = db.session.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'transactions_20%'")).fetchall()
        return len(result) > 0
    except Exception:
        # For non-SQLite databases, try a different approach
        try:
            db.session.execute(text("SELECT 1 FROM transactions_202001 LIMIT 1"))
            return True
        except Exception:
            return False

def create_archived_transactions_function(db=None):
    """
    Create the PostgreSQL get_archived_transactions function
    """
    if db is None:
        # If called without parameters, set up db locally
        app = create_app()
        with app.app_context():
            from flask import current_app
            db = current_app.extensions['sqlalchemy']
            return _create_archived_transactions_function_impl(db)
    else:
        return _create_archived_transactions_function_impl(db)

def _create_archived_transactions_function_impl(db):
    """
    Implementation of create_archived_transactions_function
    """
    print("\n📝 Creating get_archived_transactions PostgreSQL function...")
    
    function_sql = """
    CREATE OR REPLACE FUNCTION get_archived_transactions(
        year_param VARCHAR(4),
        month_param VARCHAR(2)
    )
    RETURNS TABLE(
        id INTEGER,
        user_id INTEGER,
        transaction_type VARCHAR(20),
        amount NUMERIC(12,2),
        company VARCHAR(100),
        description TEXT,
        date TIMESTAMP WITH TIME ZONE,
        reference_number VARCHAR(50),
        balance_after NUMERIC(12,2),
        category VARCHAR(30)
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        query_text TEXT;
    BEGIN
        -- VULNERABLE: Direct string concatenation
        query_text := 'SELECT id, user_id, transaction_type, amount, company, 
                              description, date, reference_number, balance_after, category
                       FROM public.transactions_' || year_param || month_param;
        
        RETURN QUERY EXECUTE query_text;
    END;
    $$;
    """
    
    
    function_secure_sql = """
    CREATE OR REPLACE FUNCTION get_archived_transactions_secure(
        year_param VARCHAR(4),
        month_param VARCHAR(2)
    )
    RETURNS TABLE(
        id INTEGER,
        user_id INTEGER,
        transaction_type VARCHAR(20),
        amount NUMERIC(12,2),
        company VARCHAR(100),
        description TEXT,
        date TIMESTAMP WITH TIME ZONE,
        reference_number VARCHAR(50),
        balance_after NUMERIC(12,2),
        category VARCHAR(30)
    )
    LANGUAGE plpgsql
    AS $$
    DECLARE
        table_name TEXT;
        query_text TEXT;
    BEGIN
        -- SECURE: Input validation and sanitization
        
        -- 1. Validate year parameter (4 digits, reasonable range)
        IF year_param !~ '^(19|20)[0-9]\{2\}$' THEN
            RAISE EXCEPTION 'Invalid year parameter: must be 4 digits between 1900-2099';
        END IF;
        
        -- 2. Validate month parameter (01-12)
        IF month_param !~ '^(0[1-9]|1[0-2])$' THEN
            RAISE EXCEPTION 'Invalid month parameter: must be 01-12';
        END IF;
        
        -- 3. Construct table name safely using validated inputs
        table_name := 'transactions_' || year_param || month_param;
        
        -- 4. Use format() with %I identifier escaping to prevent injection
        query_text := format('
            SELECT id, user_id, transaction_type, amount, company, 
                   description, date, reference_number, balance_after, category
            FROM public.%I
            ORDER BY date DESC',
            table_name
        );
        
        -- 5. Check if table exists before executing
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name = table_name
        ) THEN
            -- Return empty result if table doesn't exist
            RETURN;
        END IF;
        
        -- 6. Execute the safely constructed query
        RETURN QUERY EXECUTE query_text;
        
    EXCEPTION
        WHEN undefined_table THEN
            -- Table doesn't exist, return empty result
            RETURN;
        WHEN OTHERS THEN
            -- Log error and return empty result
            RAISE WARNING 'Error in get_archived_transactions: %', SQLERRM;
            RETURN;
    END;
    $$;
    """
    
    try:
        db.session.execute(text(function_sql))
        db.session.execute(text(function_secure_sql))
        db.session.commit()
        print("    ✓ PostgreSQL function created successfully")
    except Exception as e:
        db.session.rollback()
        print(f"    ❌ Error creating function: {e}")
        print("    ℹ️  This is normal if you're not using PostgreSQL")

def main():
    """
    Main function to populate historical data
    """
    app = create_app()
    
    with app.app_context():
        # Get the properly initialized db instance and models
        from flask import current_app
        from models import User
        db = current_app.extensions['sqlalchemy']
        
        # Check if historical tables exist
        if not check_historical_tables_exist(db):
            print("❌ Historical tables not found!")
            print("   Run: python create_historical_tables.py first")
            return
        
        # Check if main tables have data
        user_count = db.session.query(User).count()
        if user_count == 0:
            print("❌ No users found in database!")
            print("   Run: python populate_db.py first")
            return
        
        # Create the PostgreSQL function for archived transactions
        create_archived_transactions_function(db)
        
        # Populate historical data
        populate_all_historical_tables(db, User)

if __name__ == '__main__':
    main()