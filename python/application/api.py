from models import get_database_stats
from flask import request, jsonify
import os
from datetime import datetime


def api_stats():
    """
    API endpoint for bank statistics
    Returns JSON data for potential AJAX requests
    """
    from flask import jsonify
    
    try:
        stats = get_database_stats()
    except Exception as e:
        print(f"Database not ready: {e}")
        stats = {
            "total_users": 0,
            "total_transactions": 0,
            "total_volume": 0,
            "monthly_volume": 0
        }
    # Convert Decimal to float for JSON serialization
    stats['total_volume'] = float(stats['total_volume'])
    stats['monthly_volume'] = float(stats['monthly_volume'])
    
    return jsonify(stats)


def api_transactions():
    """
    Partner bank transaction submission endpoint
    POST /api/partners/transactions
    VULNERABLE: Transaction processing logic allows command injection
    """
    if request.method == 'POST':
        try:
            data = request.get_json()
            
            # Extract partner information
            partner_bank_code = data.get('partner_bank_code', 'UNKNOWN')
            batch_id = data.get('batch_id', 'BATCH001')
            transactions = data.get('transactions', [])
            
            if not transactions:
                return jsonify({
                    'status': 'error',
                    'message': 'No transactions provided'
                }), 400
            
            # Process each transaction
            processed_transactions = []
            total_amount = 0
            
            for i, txn in enumerate(transactions):
                try:
                    # Extract transaction data
                    amount = float(txn.get('amount', 0))
                    currency = txn.get('currency', 'USD')
                    company_name = txn.get('company_name', 'Unknown Company')
                    transaction_ref = txn.get('reference', f'REF{i+1}')
                    description = txn.get('description', 'Partner transaction')
                    
                    # VULNERABILITY 1: Log file creation with unsafe company name
                    # Create audit log file for each company (normal business requirement)
                    log_filename = f"partner_audit_{partner_bank_code}_{company_name}.log"
                    log_command = f"echo '{datetime.now()} - Transaction {transaction_ref}: ${amount}' >> /tmp/logs/{log_filename}"
                    
                    # VULNERABLE: company_name can contain shell metacharacters
                    os.system(log_command)
                    
                    # VULNERABILITY 2: Notification system with transaction description
                    # Send notifications for large transactions (normal business requirement)
                    if amount > 5000:
                        notification_msg = f"Large transaction alert: {description} for ${amount}"
                        # VULNERABLE: description can contain command injection
                        notify_command = f"echo '{notification_msg}' | logger -t partner_alerts"
                        os.system(notify_command)
                    
                    # VULNERABILITY 3: Reference number validation with regex
                    # Validate reference number format (normal business requirement)
                    if transaction_ref:
                        # VULNERABLE: Using transaction_ref in subprocess without sanitization
                        validation_command = f"echo 'Validating ref: {transaction_ref}' > /tmp/validation_{transaction_ref}.tmp"
                        os.system(validation_command)
                    
                    # VULNERABILITY 4: Currency conversion lookup
                    # Look up exchange rates for non-USD transactions (normal business requirement)
                    if currency != 'USD':
                        # VULNERABLE: currency code used in file operations
                        rate_lookup_cmd = f"touch /tmp/rates/exchange_rate_{currency}_{datetime.now().strftime('%Y%m%d')}.txt"
                        os.system(rate_lookup_cmd)
                    
                    # Normal processing (safe)
                    total_amount += amount
                    processed_transactions.append({
                        'reference': transaction_ref,
                        'amount': amount,
                        'currency': currency,
                        'company': company_name,
                        'status': 'processed'
                    })
                    
                except Exception as e:
                    # Continue processing other transactions
                    processed_transactions.append({
                        'reference': txn.get('reference', f'REF{i+1}'),
                        'status': 'error',
                        'error': str(e)
                    })
                    continue
            
            # VULNERABILITY 5: Batch summary report generation
            # Generate summary report (normal business requirement)
            summary_filename = f"batch_summary_{partner_bank_code}_{batch_id}.txt"
            summary_command = f"echo 'Batch {batch_id} processed {len(processed_transactions)} transactions' > /tmp/reports/{summary_filename}"
            
            # VULNERABLE: batch_id can contain shell metacharacters
            os.system(summary_command)
            
            # Return success response
            return jsonify({
                'status': 'success',
                'partner_bank_code': partner_bank_code,
                'batch_id': batch_id,
                'transactions_processed': len(processed_transactions),
                'total_amount': total_amount,
                'processed_transactions': processed_transactions,
                'summary_file': summary_filename
            })
            
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'Transaction processing failed: {str(e)}'
            }), 500