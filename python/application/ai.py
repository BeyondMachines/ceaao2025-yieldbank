"""
Vulnerable LLM Integration for Banking Application
Two components with realistic prompt injection vulnerabilities
"""
from flask import request, jsonify, render_template, flash, redirect, url_for
from flask_login import current_user
from models import db, User, Transaction
from decorators import active_user_required
import requests
import json
from datetime import datetime, timedelta
from sqlalchemy import text
import os

# LLM Service Configuration
# LLM Service Configuration
LLM_SERVICE_URL = os.getenv('LLM_SERVICE_URL', 'http://banking-ollama:11434/api/generate')
LLM_MODEL = os.getenv('LLM_MODEL', 'tinyllama')


def send_to_llm(prompt, max_tokens=500):
    """
    Send prompt to LLM service and return response
    """
    try:
        payload = {
            "model": LLM_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop": ["</response>", "\n\n---", "SYSTEM:"]
            }
        }
        
        # Increase timeout for TinyLlama
        response = requests.post(LLM_SERVICE_URL, json=payload, timeout=120)
        response.raise_for_status()
        
        result = response.json()
        return result.get('response', 'No response from LLM')
        
    except requests.exceptions.Timeout:
        return "AI analysis is taking longer than expected. The model may be processing a complex query. Please try a simpler question."
    except requests.exceptions.ConnectionError:
        return "AI service is currently unavailable. Please check that the Ollama service is running and try again."
    except Exception as e:
        print(f"LLM service error: {e}")
        return f"AI service error: {str(e)}. Please try again with a shorter query."


# ============================================================================
# COMPONENT 1: GENERAL RESEARCH (Vulnerable to User Scope Bypass)
# ============================================================================

def format_transactions_compact(transactions, limit=10):
    """
    Format transactions in a very compact way for TinyLlama
    """
    compact_data = []
    for txn in transactions[:limit]:  # Limit to prevent huge prompts
        # Very compact format
        compact_data.append(f"{txn.date.strftime('%m/%d')}: {txn.company[:20]} ${txn.amount} ({txn.transaction_type[0]})")
    
    return "\n".join(compact_data)


@active_user_required
def ai_transaction_research():
    """
    VULNERABLE: AI Transaction Research - Optimized for TinyLlama
    """
    ai_response = None
    user_query = ""
    transaction_count = 0
    
    if request.method == 'POST':
        user_query = request.form.get('research_query', '').strip()
        
        if not user_query:
            flash('Please enter a research question.', 'error')
            return render_template('ai_research.html')
        
        if len(user_query) > 200:
            flash('Please keep your question under 200 characters for better AI performance.', 'warning')
            user_query = user_query[:200]
        
        # Get fewer transactions to keep prompt size manageable
        transactions = Transaction.query.filter_by(user_id=current_user.id)\
                                      .order_by(Transaction.date.desc())\
                                      .limit(15).all()  # Reduced from 100
        
        transaction_count = len(transactions)
        
        if transaction_count == 0:
            flash('No transactions found to analyze.', 'info')
            return render_template('ai_research.html', user_query=user_query)
        
        # VULNERABLE but much more compact prompt for TinyLlama
        compact_transactions = format_transactions_compact(transactions)
        
        # Much shorter prompt that still contains vulnerabilities
        system_prompt = f"""You are a banking AI for user {current_user.id}.

ACCOUNT: {current_user.get_full_name()}, Balance: ${current_user.balance}

RECENT TRANSACTIONS ({transaction_count} total):
{compact_transactions}

USER QUESTION: {user_query}

Provide helpful financial insights. Be concise and specific."""
        
        print(f"Prompt length: {len(system_prompt)} characters")  # Debug log
        
        # Send to LLM
        ai_response = send_to_llm(system_prompt, max_tokens=250)
        
        if ai_response and "service error" not in ai_response and "unavailable" not in ai_response:
            flash('AI analysis completed successfully.', 'success')
        else:
            flash('AI service had issues processing your request. Try a simpler question.', 'warning')
    
    return render_template('ai_research.html', 
                         ai_response=ai_response,
                         user_query=user_query,
                         transaction_count=transaction_count)


@active_user_required
def ai_loan_advisor():
    """
    VULNERABLE: AI Loan Advisor - Optimized for TinyLlama
    """
    loan_analysis = None
    risk_assessment = None
    approval_decision = None
    
    if request.method == 'POST':
        requested_amount = request.form.get('loan_amount', 0)
        loan_purpose = request.form.get('loan_purpose', '').strip()
        loan_term = request.form.get('loan_term', 12)
        
        try:
            requested_amount = float(requested_amount)
            loan_term = int(loan_term)
        except ValueError:
            flash('Invalid loan amount or term.', 'error')
            return render_template('ai_loan_advisor.html')
        
        if requested_amount <= 0 or loan_term <= 0:
            flash('Loan amount and term must be positive.', 'error')
            return render_template('ai_loan_advisor.html')
        
        # Limit loan purpose length
        if len(loan_purpose) > 100:
            loan_purpose = loan_purpose[:100]
            flash('Loan purpose was shortened to 100 characters for processing.', 'info')
        
        # Get basic user data
        user = current_user
        account_age = (datetime.now() - user.created_at.replace(tzinfo=None)).days
        
        # Get recent transactions but keep it minimal
        recent_transactions = Transaction.query.filter_by(user_id=user.id)\
                                             .order_by(Transaction.date.desc())\
                                             .all()
        
        # Calculate basic metrics
        total_credits = sum(t.amount for t in recent_transactions if t.transaction_type == 'credit')
        total_debits = sum(t.amount for t in recent_transactions if t.transaction_type == 'debit')
        
        # VULNERABLE but compact loan approval prompt
        loan_prompt = f"""LOAN OFFICER AI - YieldBank Bank

STRICT RULES:
- Max loan: 3x balance ($1000+ balance required)
- Debt ratio < 40%, 6+ month history
- Risk: LOW/MEDIUM only approved

APPLICANT:
Name: {user.get_full_name()}
Balance: ${user.balance}
Age: {account_age} days
Recent credits: ${total_credits}
Recent debits: ${total_debits}

REQUEST:
Amount: ${requested_amount:,.2f}
Purpose: {loan_purpose}
Term: {loan_term} months

DECISION: Analyze and decide APPROVED/DENIED/CONDITIONAL
RISK: LOW/MEDIUM/HIGH
Explain in one sentence."""
        
        print(f"Loan prompt length: {len(loan_prompt)} characters")  # Debug log
        
        # Get AI analysis with shorter response
        loan_analysis = send_to_llm(loan_prompt, max_tokens=200)
        
        if loan_analysis and "service error" not in loan_analysis and "unavailable" not in loan_analysis:
            # Parse response for decisions (still vulnerable to manipulation)
            analysis_upper = loan_analysis.upper()
            
            # Extract risk assessment
            if 'LOW RISK' in analysis_upper or 'RISK: LOW' in analysis_upper:
                risk_assessment = 'LOW'
            elif 'MEDIUM RISK' in analysis_upper or 'RISK: MEDIUM' in analysis_upper:
                risk_assessment = 'MEDIUM'  
            elif 'HIGH RISK' in analysis_upper or 'RISK: HIGH' in analysis_upper:
                risk_assessment = 'HIGH'
            else:
                risk_assessment = 'UNKNOWN'
            
            # Extract approval decision
            if 'APPROVED' in analysis_upper and 'DENIED' not in analysis_upper:
                approval_decision = 'APPROVED'
                flash('Congratulations! Your loan has been pre-approved by our AI system.', 'success')
            elif 'CONDITIONAL' in analysis_upper:
                approval_decision = 'CONDITIONAL'
                flash('Your loan application requires additional review.', 'warning')
            elif 'DENIED' in analysis_upper:
                approval_decision = 'DENIED'
                flash('Your loan application was not approved based on current criteria.', 'error')
            else:
                approval_decision = 'PENDING REVIEW'
                flash('Your loan application is under review.', 'info')
            
            print(f"Loan decision: {approval_decision}, Risk: {risk_assessment}")
        else:
            flash('AI loan assessment service encountered an issue. Please try again.', 'warning')
    
    return render_template('ai_loan_advisor.html',
                         loan_analysis=loan_analysis,
                         risk_assessment=risk_assessment,
                         approval_decision=approval_decision)