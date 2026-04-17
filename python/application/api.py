from models import get_database_stats
from flask import request, jsonify
from datetime import datetime
from pathlib import Path
import re


def _safe_token(value, default="unknown"):
    token = re.sub(r"[^a-zA-Z0-9_-]", "_", str(value or "").strip())
    return token or default


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
    Partner bank transaction submission endpoint.
    Uses safe file operations only (no shell execution).
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
                    currency = str(txn.get('currency', 'USD')).upper()
                    company_name = txn.get('company_name', 'Unknown Company')
                    transaction_ref = txn.get('reference', f'REF{i+1}')
                    description = txn.get('description', 'Partner transaction')

                    safe_bank = _safe_token(partner_bank_code, "bank")
                    safe_company = _safe_token(company_name, "company")
                    safe_ref = _safe_token(transaction_ref, f"ref{i+1}")
                    safe_batch = _safe_token(batch_id, "batch")

                    logs_dir = Path("/tmp/logs")
                    logs_dir.mkdir(parents=True, exist_ok=True)
                    reports_dir = Path("/tmp/reports")
                    reports_dir.mkdir(parents=True, exist_ok=True)
                    rates_dir = Path("/tmp/rates")
                    rates_dir.mkdir(parents=True, exist_ok=True)

                    # Safe audit log write
                    log_filename = logs_dir / f"partner_audit_{safe_bank}_{safe_company}.log"
                    with log_filename.open("a", encoding="utf-8") as f:
                        f.write(f"{datetime.now().isoformat()} - Transaction {safe_ref}: ${amount}\n")

                    # Safe notification write
                    if amount > 5000:
                        notification_msg = f"Large transaction alert: {description} for ${amount}"
                        notify_file = logs_dir / "partner_alerts.log"
                        with notify_file.open("a", encoding="utf-8") as f:
                            f.write(notification_msg + "\n")

                    # Safe validation artifact
                    if transaction_ref:
                        validation_file = logs_dir / f"validation_{safe_ref}.tmp"
                        validation_file.write_text(f"Validating ref: {safe_ref}\n", encoding="utf-8")

                    # Safe rate lookup artifact
                    if currency != 'USD':
                        safe_currency = _safe_token(currency, "USD")
                        rate_file = rates_dir / f"exchange_rate_{safe_currency}_{datetime.now().strftime('%Y%m%d')}.txt"
                        rate_file.touch(exist_ok=True)
                    
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
            
            # Generate summary report safely
            safe_bank = _safe_token(partner_bank_code, "bank")
            safe_batch = _safe_token(batch_id, "batch")
            summary_filename = f"batch_summary_{safe_bank}_{safe_batch}.txt"
            summary_path = Path("/tmp/reports") / summary_filename
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(
                f"Batch {batch_id} processed {len(processed_transactions)} transactions\n",
                encoding="utf-8",
            )
            
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
