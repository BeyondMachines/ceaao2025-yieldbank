import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, text
from models import db, User, Transaction
from decorators import login_required, anonymous_required, active_user_required
import subprocess
import csv
import pickle
import os
import json
import yaml
from jinja2 import Template
from decimal import Decimal, InvalidOperation
import logging
import re
from pathlib import Path
import html


@active_user_required
def transaction_detail(transaction_id):
    """
    Detailed view of a specific transaction with note editing capability
    Shows all transaction information and related data
    Handles note updates with VULNERABLE template injection
    """
    # Get transaction and verify it belongs to current user
    # transaction = Transaction.query.filter_by(
    #     id=transaction_id,
    #     user_id=current_user.id
    # ).first()
     # VULNERABLE IDOR: No user ownership check
    transaction = Transaction.query.get(transaction_id)

    if not transaction:
        flash('Transaction not found or you do not have permission to view it.', 'error')
        return redirect(url_for('dashboard'))
    
    # Handle note update via POST
    if request.method == 'POST':
        new_note = request.form.get('transaction_note', '').strip()
        
        try:
            # Update the note
            transaction.note = new_note if new_note else None
            db.session.commit()
            if new_note:
                flash('Transaction note updated successfully.', 'success')
            else:
                flash('Transaction note cleared.', 'info')

        except Exception as e:
            db.session.rollback()
            flash(f'Error updating note: {str(e)}', 'error')
    
    # Get related transactions (same company, recent)
    related_transactions = Transaction.query.filter(
        and_(
            Transaction.user_id == current_user.id,
            Transaction.company == transaction.company,
            Transaction.id != transaction.id
        )
    ).order_by(Transaction.date.desc()).limit(5).all()
    
    # VULNERABLE: Process note through Jinja2 template rendering

    # IN-UNIVERSE: Since the note can have limited html functionality, we will render it separately, so that we can have control of any errors,
    # and also show the raw note if rendering fails.
    # This also allows protection against XSS by controlling the rendering context.
    rendered_note = None
    if transaction.note:
        try:
            # VULNERABILITY: Direct template rendering of user input
            # This allows template injection attacks

            template = Template(transaction.note)
            rendered_note = template.render(
                current_user=current_user,
                transaction=transaction,
                config=current_app.config,
                request=request
            )
            # END VULNERABILITY 

        except Exception as e:
            # If template rendering fails, show the raw note
            rendered_note = transaction.note
            flash(f'Note rendering error: {str(e)}', 'warning')
    
    return render_template('transaction.html', 
                            transaction=transaction, 
                            related_transactions=related_transactions,
                            rendered_note=rendered_note)



@active_user_required
def search():
    """
    Transaction search functionality with both Basic and Advanced search modes
    Basic search uses safe ORM queries
    Advanced search uses raw SQL for "better performance" (contains SQL injection vulnerabilities)
    """
    transactions = []
    search_performed = False
    search_mode = request.form.get('search_mode', 'basic') if request.method == 'POST' else 'basic'
    
    if request.method == 'POST':
        search_performed = True
        
        if search_mode == 'basic':
            # SAFE: Basic search using ORM (existing functionality)
            transactions = _basic_search()
        else:
            # VULNERABLE: Advanced search using raw SQL
            transactions = _advanced_search()
    
    return render_template('search.html', 
                         transactions=transactions, 
                         search_performed=search_performed,
                         search_mode=search_mode)


def _basic_search():
    """
    Safe basic search using SQLAlchemy ORM (original implementation)
    """
    company = request.form.get('company', '').strip()
    date_from = request.form.get('date_from', '').strip()
    date_to = request.form.get('date_to', '').strip()
    
    # Build query safely using ORM
    query = Transaction.query.filter_by(user_id=current_user.id)
    
    # Add company filter if provided
    if company:
        query = query.filter(Transaction.company.ilike(f'%{company}%'))
    
    # Add date filters if provided
    if date_from:
        try:
            date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Transaction.date >= date_from_obj)
        except ValueError:
            flash('Invalid start date format.', 'error')
            return []
    
    if date_to:
        try:
            date_to_obj = datetime.strptime(date_to, '%Y-%m-%d')
            date_to_obj = date_to_obj + timedelta(days=1)
            query = query.filter(Transaction.date < date_to_obj)
        except ValueError:
            flash('Invalid end date format.', 'error')
            return []
    
    # Get results
    transactions = query.order_by(Transaction.date.desc()).limit(100).all()
    
    if not transactions:
        flash('No transactions found matching your search criteria.', 'info')
    else:
        flash(f'Found {len(transactions)} transaction(s).', 'success')
    
    return transactions


def _advanced_search():
    """
    VULNERABLE: Advanced search using raw SQL for "better performance and flexibility"
    Contains multiple SQL injection vulnerabilities for training purposes
    """
    # Get advanced search parameters
    company = request.form.get('adv_company', '').strip()
    amount_min = request.form.get('amount_min', '').strip()
    amount_max = request.form.get('amount_max', '').strip()
    transaction_type = request.form.get('transaction_type', '').strip()
    category = request.form.get('category', '').strip()
    date_from = request.form.get('adv_date_from', '').strip()
    date_to = request.form.get('adv_date_to', '').strip()
    sort_by = request.form.get('sort_by', 'date').strip()
    sort_order = request.form.get('sort_order', 'DESC').strip()
    
    # VULNERABILITY 1: Dynamic WHERE clause building with string concatenation
    base_query = f"""
        SELECT t.*, u.first_name, u.last_name 
        FROM transactions t 
        JOIN users u ON t.user_id = u.id 
        WHERE t.user_id = {current_user.id}
    """
    
    where_conditions = []
    
    # VULNERABILITY 2: Unsafe company name filtering
    if company:
        # This allows SQL injection via company name parameter
        where_conditions.append(f"t.company LIKE '%{company}%'")
    
    # VULNERABILITY 3: Unsafe amount range filtering
    if amount_min:
        # Direct injection of user input into SQL
        where_conditions.append(f"t.amount >= {amount_min}")
    
    if amount_max:
        # Another injection point
        where_conditions.append(f"t.amount <= {amount_max}")
    
    # VULNERABILITY 4: Unsafe transaction type filtering
    if transaction_type and transaction_type.lower() != 'all':
        # Using user input directly in SQL
        where_conditions.append(f"t.transaction_type = '{transaction_type}'")
    
    # VULNERABILITY 5: Category filtering injection
    if category:
        # Another string concatenation vulnerability
        where_conditions.append(f"t.category LIKE '%{category}%'")
    
    # VULNERABILITY 6: Date filtering vulnerabilities
    if date_from:
        # Date injection - users could inject SQL instead of dates
        where_conditions.append(f"t.date >= '{date_from}'")
    
    if date_to:
        # Another date injection point
        where_conditions.append(f"t.date <= '{date_to} 23:59:59'")
    
    # Build the complete WHERE clause
    if where_conditions:
        base_query += " AND " + " AND ".join(where_conditions)
    
    # VULNERABILITY 7: Unsafe ORDER BY clause
    # This allows injection via sort parameters
    base_query += f" ORDER BY t.{sort_by} {sort_order}"
    
    # VULNERABILITY 8: Unsafe LIMIT clause (bonus injection point)
    limit = request.form.get('limit', '100').strip()
    base_query += f" LIMIT {limit}"
    
    # Add some logging for "debugging" purposes (reveals the vulnerable query)
    print(f"DEBUG: Executing advanced search query: {base_query}")
    
    try:
        # Execute the vulnerable raw SQL query
        result = db.session.execute(text(base_query))
        
        # Convert results back to Transaction objects
        transactions = []
        for row in result:
            # Assuming your SELECT returns transaction columns in order
            transaction = db.session.get(Transaction, row.id)  # Add model class
            if transaction:
                transactions.append(transaction)

        if not transactions:
            flash('No transactions found matching your advanced search criteria.', 'info')
        else:
            flash(f'Advanced search found {len(transactions)} transaction(s).', 'success')
        
        return transactions
        
    except Exception as e:
        # VULNERABILITY 9: Error message that reveals database structure
        error_msg = str(e)
        flash(f'Advanced search failed: {error_msg}', 'error')
        print(f"Advanced search error: {e}")
        return []
    

def transaction_analytics():
    """
    VULNERABLE: New analytics feature with multiple SQL injection points
    Could be added as a new route for "power users"
    """
    # Get analytics parameters
    metric = request.args.get('metric', 'monthly_spending').strip()
    group_by = request.args.get('group_by', 'company').strip()
    time_period = request.args.get('time_period', '6').strip()  # months
    
    # VULNERABILITY 11: Dynamic analytics query building
    analytics_query = f"""
        SELECT 
            {group_by},
            COUNT(*) as transaction_count,
            SUM(amount) as total_amount,
            AVG(amount) as avg_amount
        FROM transactions 
        WHERE user_id = {current_user.id}
        AND date >= DATE('now', '-{time_period} months')
        GROUP BY {group_by}
        ORDER BY total_amount DESC
    """
    
    # VULNERABILITY 12: Optional custom WHERE clause
    custom_filter = request.args.get('custom_filter', '').strip()
    if custom_filter:
        analytics_query += f" HAVING {custom_filter}"
    
    try:
        result = db.session.execute(text(analytics_query))
        return [dict(row) for row in result]
    except Exception as e:
        flash(f'Analytics query failed: {error}', 'error')
        return []


# Additional vulnerable helper functions that could be used in various places

def get_transaction_by_reference(reference_number):
    """
    VULNERABILITY 13: Unsafe transaction lookup by reference number
    """
    # Direct string interpolation in SQL query
    query = f"""
        SELECT * FROM transactions 
        WHERE user_id = {current_user.id} 
        AND reference_number = '{reference_number}'
    """
    
    try:
        result = db.session.execute(text(query))
        row = result.fetchone()
        if row:
            return db.session.get(row[0])
        return None
    except Exception as e:
        print(f"Reference lookup error: {e}")
        return None


@active_user_required  
def export_transactions():
    """
    VULNERABLE: Export transactions with customizable filename and format
    Contains command injection via filename and format parameters
    """
    export_results = None

    if request.method == 'POST':
        filename = request.form.get('filename', 'transactions').strip()
        date_range = request.form.get('date_range', '30').strip()

        export_format = 'csv'

        print(export_format, filename, date_range)
        # Get user's transactions
        days = int(date_range) if date_range.isdigit() else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= cutoff_date
        ).order_by(Transaction.date.desc()).all()

        # VULNERABILITY: User input directly passed to shell command
        export_path = f"/tmp/exports/{filename}"
        
        try:
            # Create directory and file with command injection vulnerability
            command = f"mkdir -p /tmp/exports && touch {export_path}"
            
    
            # Execute the vulnerable command
            print(f"DEBUG: Executing command: {command}")
            result = subprocess.run(command, shell=True, capture_output=True, text=True)

            # Generate actual CSV content
            with open(export_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['Date', 'Company', 'Type', 'Amount', 'Balance', 'Reference'])
                
                for txn in transactions:
                    writer.writerow([
                        txn.date.strftime('%Y-%m-%d %H:%M:%S'),
                        txn.company,
                        txn.transaction_type,
                        txn.amount,
                        txn.balance_after,
                        txn.reference_number
                    ])
            
            # Prepare results for template display
            export_results = {
                'success': result.returncode == 0,
                'filename': f"{filename}.{export_format}",
                'transaction_count': len(transactions),
                'output': result.stdout,
                'error': result.stderr,
                'file_exists': os.path.exists(export_path)
            }
            
            if result.returncode == 0:
                flash(f'Export generated successfully! results: {result.stdout}, {result.stderr}', 'success')
            else:
                flash('Export command failed. See details below.', 'error')


        except Exception as e:
            flash(f'Export error: {str(e)}', 'error')
            export_results = {
                'success': False,
                'filename': f"{filename}.{export_format}",
                'error': str(e)
            }
    
    return render_template('export.html', export_results=export_results)


@active_user_required
def download_export_file():
    """Download the generated export file"""
    filename = request.args.get('filename', 'transactions.csv')
    file_path = f"/tmp/exports/{filename.replace('.csv', '')}"  # Remove extension since we add it in export
    
    try:
        if os.path.exists(file_path):
            return send_file(
                file_path,
                as_attachment=True,
                download_name=filename,
                mimetype='text/csv'
            )
        else:
            flash('Export file not found. Please generate a new export.', 'error')
            return redirect(url_for('export_transactions'))
    except Exception as e:
        flash(f'Download error: {str(e)}', 'error')
        return redirect(url_for('export_transactions'))
    

@active_user_required
def import_transactions():
    """
    VULNERABLE: Import transactions using YAML configuration files
    Accepts YAML config files that can instantiate Python objects
    """
    if request.method == 'POST':
        if 'import_file' not in request.files:
            flash('No file selected for import.', 'error')
            return redirect(url_for('import_transactions'))
        
        file = request.files['import_file']
        import_format = request.form.get('import_format', 'standard')
        
        if file.filename == '':
            flash('No file selected.', 'error')
            return redirect(url_for('import_transactions'))
        
        try:
            file_content = file.read().decode('utf-8')
            
            if import_format == 'yaml_config':
                # "YAML configuration files for complex import rules"
                print(f"DEBUG: Processing YAML configuration from {file.filename}")
                
                # VULNERABLE: yaml.load() can execute arbitrary Python code
                config = yaml.load(file_content, Loader=yaml.Loader)

                # Process the configuration
                if config:
                    imported_count = config.get('transaction_count', 0)
                    import_rules = config.get('import_rules', {})
                    
                    flash(f'YAML configuration loaded: {imported_count} transactions, {len(import_rules)} rules', 'success')
                
            elif import_format == 'json_template':
                # "JSON template with processing instructions"
                print(f"DEBUG: Processing JSON template from {file.filename}")
                
                template = json.loads(file_content)
                
                # VULNERABILITY: Execute any "preprocessing" commands
                if 'preprocessing' in template:
                    for cmd in template['preprocessing']:
                        if 'command' in cmd:
                            # VULNERABLE: Execute preprocessing commands
                            result = eval(cmd['command'])
                            print(f"DEBUG: Executed preprocessing: {cmd['command']} -> {result}")
                
                # Process template formulas
                if 'formulas' in template:
                    for formula_name, formula_code in template['formulas'].items():
                        # VULNERABLE: eval() on template formulas
                        result = eval(formula_code)
                        template[f'formula_{formula_name}_result'] = result

                transactions = template.get('transactions', [])
                flash(f'JSON template processed: {len(transactions)} transactions', 'success')
                
            elif import_format == 'config_script':
                # "Configuration script for advanced import logic"
                print(f"DEBUG: Processing configuration script from {file.filename}")
                
                # VULNERABLE: Execute configuration as Python code
                exec(file_content)
                flash('Configuration script executed successfully', 'success')
                
            else:
                # Safe CSV import (not vulnerable)
                flash('Standard CSV import completed (simulated)', 'info')
                
        except yaml.YAMLError as e:
            flash(f'YAML parsing error: {str(e)}', 'error')
        except json.JSONDecodeError as e:
            flash(f'JSON parsing error: {str(e)}', 'error')
        except Exception as e:
            flash(f'Import failed: {str(e)}', 'error')
    
    return render_template('import.html')

def _call_archived_transactions_procedure(year, month):
    """
    Call the get_archived_transactions stored procedure with year and month parameters
    Returns a list of transaction-like objects filtered by current user
    """
    try:
        # PostgreSQL function call with user filter
        procedure_call = "SELECT * FROM get_archived_transactions(:year, :month) WHERE user_id = :user_id"
        
        result = db.session.execute(
            text(procedure_call),
            {'year': year, 'month': month, 'user_id': current_user.id}
        )
        
        # Convert result rows to transaction-like objects
        transactions = []
        
        for row in result:
            # Create a simple object to hold the transaction data
            # Assuming the stored procedure returns columns matching Transaction model
            transaction = type('ArchivedTransaction', (), {})()
            
            # Map common transaction fields - adjust based on your stored procedure output
            transaction.id = getattr(row, 'id', None)
            transaction.date = getattr(row, 'date', None) 
            transaction.company = getattr(row, 'company', '')
            transaction.description = getattr(row, 'description', '')
            transaction.amount = getattr(row, 'amount', 0)
            transaction.balance_after = getattr(row, 'balance_after', 0)
            transaction.reference_number = getattr(row, 'reference_number', '')
            transaction.transaction_type = getattr(row, 'transaction_type', '')
            transaction.category = getattr(row, 'category', '')
            transaction.user_id = getattr(row, 'user_id', current_user.id)
            
            # Add helper method for credit/debit checking
            def is_credit_method():
                return getattr(transaction, 'transaction_type', '').lower() == 'credit'
            transaction.is_credit = is_credit_method
            
            transactions.append(transaction)
            
        return transactions
        
    except Exception as e:
        print(f"Stored procedure call error: {e}")
        flash(f'Database error: {str(e)}', 'error')
        return []

@active_user_required
def transaction_archive():
    """
    View and manage archived transactions using stored procedures
    Accepts year and month parameters to call get_archived_transactions stored procedure
    """
    transactions = []
    archive_performed = False
    selected_year = None
    selected_month = None
    
    # Available years for dropdown
    available_years = ['2020', '2021']
    
    # Available months for dropdown
    available_months = [
        ('01', 'January'), ('02', 'February'), ('03', 'March'),
        ('04', 'April'), ('05', 'May'), ('06', 'June'),
        ('07', 'July'), ('08', 'August'), ('09', 'September'),
        ('10', 'October'), ('11', 'November'), ('12', 'December')
    ]
    
    if request.method == 'POST':
        archive_performed = True
        selected_year = request.form.get('archive_year', '')
        selected_month = request.form.get('archive_month', '')
        
        if selected_year and selected_month:
            try:
                # Call the stored procedure get_archived_transactions
                transactions = _call_archived_transactions_procedure(selected_year, selected_month)
                
                if transactions:
                    flash(f'Found {len(transactions)} archived transactions for {selected_month}/{selected_year}.', 'success')
                else:
                    flash(f'No archived transactions found for {selected_month}/{selected_year}.', 'info')
                    
            except Exception as e:
                flash(f'Error retrieving archived transactions: {str(e)}', 'error')
        else:
            flash('Please select both year and month.', 'error')

    # Calculate summary statistics for display
    total_credits = sum(t.amount for t in transactions if hasattr(t, 'amount') and getattr(t, 'transaction_type', '') == 'credit')
    total_debits = sum(t.amount for t in transactions if hasattr(t, 'amount') and getattr(t, 'transaction_type', '') == 'debit')
    
    summary = {
        'total_credits': total_credits,
        'total_debits': total_debits,
        'recent_activity_count': len(transactions),
        'average_score': 0
    }

    return render_template('archive.html', 
                         transactions=transactions, 
                         summary=summary,
                         archive_performed=archive_performed,
                         available_years=available_years,
                         available_months=available_months,
                         selected_year=selected_year,
                         selected_month=selected_month)