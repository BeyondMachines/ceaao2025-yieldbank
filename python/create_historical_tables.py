"""
Create historical transaction tables for 2020-2021
Reuses the Transaction model structure to create monthly tables
"""
from sqlalchemy import MetaData, Table, Column, Integer, Numeric, String, DateTime, ForeignKey, Index
from app import create_app
from datetime import datetime

def create_historical_transaction_table(table_name, db, Transaction):
    """
    Create a historical transaction table with the same structure as Transaction model
    """
    # Get the original transaction table structure
    original_table = Transaction.__table__
    
    # Create new table with same columns but different name
    historical_table = Table(
        table_name, 
        db.metadata,
        Column('id', Integer, primary_key=True),
        Column('user_id', Integer, ForeignKey('users.id'), nullable=False, index=True),
        Column('transaction_type', String(20), nullable=False),
        Column('amount', Numeric(12, 2), nullable=False),
        Column('company', String(100), nullable=False),
        Column('description', db.Text),
        Column('date', DateTime(timezone=True), nullable=False, index=True),
        Column('reference_number', String(50), unique=True, nullable=False),
        Column('balance_after', Numeric(12, 2), nullable=False),
        Column('category', String(30)),
        extend_existing=True
    )
    
    return historical_table

def create_all_historical_tables(db=None, Transaction=None):
    """
    Create historical transaction tables for 2020 and 2021 (24 tables total)
    """
    if db is None or Transaction is None:
        # If called without parameters, set up db and Transaction locally
        app = create_app()
        with app.app_context():
            from flask import current_app
            from models import Transaction as TransactionModel
            db = current_app.extensions['sqlalchemy']
            Transaction = TransactionModel
            return _create_all_historical_tables_impl(db, Transaction)
    else:
        return _create_all_historical_tables_impl(db, Transaction)

def _create_all_historical_tables_impl(db, Transaction):
    """
    Implementation of create_all_historical_tables
    """
    print("Creating historical transaction tables...")
    
    tables_created = []
    
    # Create tables for 2020 and 2021
    for year in [2020, 2021]:
        for month in range(1, 13):
            table_name = f"transactions_{year}{month:02d}"
            print(f"  Creating table: {table_name}")
            
            try:
                historical_table = create_historical_transaction_table(table_name, db, Transaction)
                tables_created.append(table_name)
            except Exception as e:
                print(f"  ❌ Error creating {table_name}: {e}")
                continue
    
    # Create all tables in database
    try:
        db.create_all()
        print(f"✓ Successfully created {len(tables_created)} historical tables")
        return tables_created
    except Exception as e:
        print(f"❌ Error creating tables in database: {e}")
        return []

def get_historical_table_name(date):
    """
    Get the historical table name for a given date
    """
    return f"transactions_{date.year}{date.month:02d}"

def insert_transaction_to_historical_table(transaction_data, table_name, db):
    """
    Insert transaction data into a specific historical table using raw SQL
    """
    insert_query = f"""
        INSERT INTO {table_name} 
        (user_id, transaction_type, amount, company, description, date, 
         reference_number, balance_after, category)
        VALUES 
        (%(user_id)s, %(transaction_type)s, %(amount)s, %(company)s, 
         %(description)s, %(date)s, %(reference_number)s, %(balance_after)s, %(category)s)
    """
    
    try:
        db.session.execute(insert_query, transaction_data)
        return True
    except Exception as e:
        print(f"Error inserting into {table_name}: {e}")
        return False

def main():
    """
    Main function to create historical tables
    """
    app = create_app()
    
    with app.app_context():
        print("=" * 60)
        print("Creating Historical Transaction Tables")
        print("=" * 60)
        
        # Create the tables
        created_tables = create_all_historical_tables()
        
        if created_tables:
            print(f"\n✅ Created {len(created_tables)} historical tables:")
            for table_name in created_tables:
                print(f"   📋 {table_name}")
            
            print("\n🚀 Ready to populate with historical data!")
            print("   Run: python populate_historical_data.py")
        else:
            print("\n❌ Failed to create historical tables")
        
        print("=" * 60)

if __name__ == '__main__':
    main()