import random
from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file, current_app
from flask_login import login_user, logout_user, current_user
from datetime import datetime, timedelta
from sqlalchemy import or_, and_, text
from models import db, User, Transaction
from decorators import login_required, anonymous_required, active_user_required
import csv
import os
import json
import yaml
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
    Handles note updates securely
    """
    # Enforce ownership check
    transaction = Transaction.query.filter_by(
        id=transaction_id,
        user_id=current_user.id
    ).first()

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
    
    # Render note as plain text only (never as template code)
    rendered_note = None
    if transaction.note:
        rendered_note = transaction.note
    
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
    Safe advanced search using ORM with validated user inputs.
    """
    company = request.form.get('adv_company', '').strip()
    amount_min = request.form.get('amount_min', '').strip()
    amount_max = request.form.get('amount_max', '').strip()
    transaction_type = request.form.get('transaction_type', '').strip()
    category = request.form.get('category', '').strip()
    date_from = request.form.get('adv_date_from', '').strip()
    date_to = request.form.get('adv_date_to', '').strip()
    sort_by = request.form.get('sort_by', 'date').strip().lower()
    sort_order = request.form.get('sort_order', 'DESC').strip().upper()
    limit_raw = request.form.get('limit', '100').strip()

    try:
        query = Transaction.query.filter(Transaction.user_id == current_user.id)

        if company:
            query = query.filter(Transaction.company.ilike(f"%{company}%"))

        if amount_min:
            query = query.filter(Transaction.amount >= Decimal(amount_min))
        if amount_max:
            query = query.filter(Transaction.amount <= Decimal(amount_max))

        if transaction_type and transaction_type.lower() != 'all':
            query = query.filter(Transaction.transaction_type == transaction_type.lower())

        if category:
            query = query.filter(Transaction.category.ilike(f"%{category}%"))

        if date_from:
            start_date = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Transaction.date >= start_date)
        if date_to:
            end_date = datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(Transaction.date < end_date)

        allowed_sort = {
            'date': Transaction.date,
            'amount': Transaction.amount,
            'company': Transaction.company,
            'type': Transaction.transaction_type,
        }
        if sort_by not in allowed_sort:
            sort_by = 'date'
        sort_col = allowed_sort[sort_by]
        if sort_order == 'ASC':
            query = query.order_by(sort_col.asc())
        else:
            query = query.order_by(sort_col.desc())

        try:
            limit = int(limit_raw)
        except ValueError:
            limit = 100
        limit = max(1, min(limit, 500))
        transactions = query.limit(limit).all()

        if not transactions:
            flash('No transactions found matching your advanced search criteria.', 'info')
        else:
            flash(f'Advanced search found {len(transactions)} transaction(s).', 'success')
        
        return transactions
        
    except (InvalidOperation, ValueError):
        flash('Invalid advanced search input.', 'error')
        return []
    except Exception as e:
        flash('Advanced search failed. Please verify inputs.', 'error')
        print(f"Advanced search error: {e}")
        return []
    

def transaction_analytics():
    """
    Safe analytics helper with validated grouping and time window.
    """
    metric = request.args.get('metric', 'monthly_spending').strip()
    group_by = request.args.get('group_by', 'company').strip().lower()
    time_period = request.args.get('time_period', '6').strip()  # months

    try:
        months = int(time_period)
    except ValueError:
        months = 6
    months = max(1, min(months, 24))
    cutoff = datetime.now() - timedelta(days=months * 30)

    group_map = {
        'company': Transaction.company,
        'type': Transaction.transaction_type,
        'category': Transaction.category,
    }
    group_col = group_map.get(group_by, Transaction.company)

    try:
        results = (
            db.session.query(
                group_col.label('group_key'),
                db.func.count(Transaction.id).label('transaction_count'),
                db.func.sum(Transaction.amount).label('total_amount'),
                db.func.avg(Transaction.amount).label('avg_amount'),
            )
            .filter(Transaction.user_id == current_user.id, Transaction.date >= cutoff)
            .group_by(group_col)
            .order_by(db.func.sum(Transaction.amount).desc())
            .all()
        )
        return [
            {
                'group': row.group_key,
                'transaction_count': int(row.transaction_count),
                'total_amount': float(row.total_amount or 0),
                'avg_amount': float(row.avg_amount or 0),
            }
            for row in results
        ]
    except Exception as e:
        flash('Analytics query failed.', 'error')
        print(f"Analytics query failed: {e}")
        return []


# Additional vulnerable helper functions that could be used in various places

def get_transaction_by_reference(reference_number):
    """
    Safe transaction lookup by reference number.
    """
    try:
        return Transaction.query.filter_by(
            user_id=current_user.id,
            reference_number=reference_number
        ).first()
    except Exception as e:
        print(f"Reference lookup error: {e}")
        return None


@active_user_required  
def export_transactions():
    """
    Export transactions safely to CSV.
    """
    export_results = None

    if request.method == 'POST':
        filename = request.form.get('filename', 'transactions').strip()
        date_range = request.form.get('date_range', '30').strip()

        export_format = 'csv'

        # Get user's transactions
        days = int(date_range) if date_range.isdigit() else 30
        cutoff_date = datetime.now() - timedelta(days=days)
        transactions = Transaction.query.filter(
            Transaction.user_id == current_user.id,
            Transaction.date >= cutoff_date
        ).order_by(Transaction.date.desc()).all()

        safe_filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename) or 'transactions'
        export_dir = Path('/tmp/exports')
        export_dir.mkdir(parents=True, exist_ok=True)
        export_path = export_dir / safe_filename
        
        try:
            # Generate actual CSV content
            with export_path.open('w', newline='', encoding='utf-8') as csvfile:
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
                'success': True,
                'filename': f"{safe_filename}.{export_format}",
                'transaction_count': len(transactions),
                'output': '',
                'error': '',
                'file_exists': export_path.exists()
            }
            
            flash('Export generated successfully.', 'success')


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
    safe_name = Path(filename).name
    base_dir = Path('/tmp/exports').resolve()
    file_path = (base_dir / safe_name.replace('.csv', '')).resolve()
    
    try:
        if not str(file_path).startswith(str(base_dir)):
            flash('Invalid download path.', 'error')
            return redirect(url_for('export_transactions'))
        if file_path.exists() and file_path.is_file():
            return send_file(
                file_path,
                as_attachment=True,
                download_name=safe_name,
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
    Safe import parser for supported non-executable formats.
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
                config = yaml.safe_load(file_content)
                if not isinstance(config, dict):
                    flash('Invalid YAML configuration structure.', 'error')
                    return redirect(url_for('import_transactions'))

                allowed_keys = {'transaction_count', 'import_rules', 'transactions'}
                unknown = set(config.keys()) - allowed_keys
                if unknown:
                    flash(f"Unsupported YAML keys: {', '.join(sorted(unknown))}", 'error')
                    return redirect(url_for('import_transactions'))

                imported_count = int(config.get('transaction_count', 0))
                import_rules = config.get('import_rules', {})
                if import_rules is not None and not isinstance(import_rules, dict):
                    flash('import_rules must be an object.', 'error')
                    return redirect(url_for('import_transactions'))
                flash(f'YAML configuration loaded safely: {imported_count} transactions, {len(import_rules)} rules', 'success')
                
            elif import_format == 'json_template':
                template = json.loads(file_content)
                if not isinstance(template, dict):
                    flash('Invalid JSON template structure.', 'error')
                    return redirect(url_for('import_transactions'))

                allowed_keys = {'transactions', 'metadata'}
                unknown = set(template.keys()) - allowed_keys
                if unknown:
                    flash(f"Unsupported JSON keys: {', '.join(sorted(unknown))}", 'error')
                    return redirect(url_for('import_transactions'))

                transactions = template.get('transactions', [])
                if not isinstance(transactions, list):
                    flash('transactions must be an array.', 'error')
                    return redirect(url_for('import_transactions'))
                flash(f'JSON template processed safely: {len(transactions)} transactions', 'success')
                
            elif import_format == 'config_script':
                flash('Script-based import is disabled for security reasons.', 'error')
                
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
