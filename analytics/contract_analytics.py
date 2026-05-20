import re
from datetime import datetime, date
import random


def extract_contract_value(text):
    """Extract monetary value from contract text."""
    # Patterns for different currency formats
    patterns = [
        r'\$\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # $10,000.00
        r'USD\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # USD 10000
        r'(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|dollars?)',  # 10000 USD
        r'(?:value|worth|amount|total|sum)(?:\s+of)?\s*\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',  # value of $10000
    ]

    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            # Get the largest value found
            values = [float(m.replace(',', '')) for m in matches]
            return max(values)

    return 0.0


def calculate_risk_score(contract_data):
    """
    Calculate risk score (0-100) based on multiple factors.

    Factors:
    - Time to expiry (shorter = higher risk)
    - Contract value (higher = higher risk)
    - Missing information
    - Contract status
    """
    risk_score = 0

    # Factor 1: Time to expiry (max 40 points)
    expiry_date = contract_data.get('expiry_date')
    if expiry_date:
        try:
            expiry = datetime.fromisoformat(expiry_date).date()
            today = date.today()
            days_remaining = (expiry - today).days

            if days_remaining < 0:
                risk_score += 40  # Expired = max risk
            elif days_remaining < 30:
                risk_score += 35  # Less than 1 month
            elif days_remaining < 90:
                risk_score += 25  # Less than 3 months
            elif days_remaining < 180:
                risk_score += 15  # Less than 6 months
            else:
                risk_score += 5   # More than 6 months
        except:
            risk_score += 10  # Invalid date = some risk
    else:
        risk_score += 15  # No expiry date = moderate risk

    # Factor 2: Contract value (max 30 points)
    contract_value = contract_data.get('contract_value', 0)
    if contract_value > 1000000:
        risk_score += 30  # > $1M = high risk
    elif contract_value > 500000:
        risk_score += 20  # > $500K
    elif contract_value > 100000:
        risk_score += 10  # > $100K
    elif contract_value > 0:
        risk_score += 5   # Some value
    else:
        risk_score += 15  # No value specified = unknown risk

    # Factor 3: Missing critical information (max 20 points)
    missing_fields = 0
    critical_fields = ['party_1_name', 'party_2_name', 'service_type', 'effective_date']
    for field in critical_fields:
        if not contract_data.get(field):
            missing_fields += 1
    risk_score += missing_fields * 5

    # Factor 4: Contract status (max 10 points)
    status = contract_data.get('status', 'Active')
    if status == 'Expired':
        risk_score += 10
    elif status == 'Pending':
        risk_score += 5
    elif status == 'Under Review':
        risk_score += 7

    # Cap at 100
    return min(risk_score, 100)


def calculate_renewal_probability(contract_data):
    """
    Calculate probability of contract renewal (0.0 to 1.0).

    Based on:
    - Historical performance (simulated)
    - Time remaining
    - Contract value
    """
    probability = 0.5  # Start at 50%

    # Factor 1: Time to expiry
    expiry_date = contract_data.get('expiry_date')
    if expiry_date:
        try:
            expiry = datetime.fromisoformat(expiry_date).date()
            today = date.today()
            days_remaining = (expiry - today).days

            if days_remaining < 0:
                probability = 0.1  # Already expired
            elif days_remaining < 30:
                probability += 0.1  # Close to expiry, urgent
            elif days_remaining < 90:
                probability += 0.2  # Good timing for renewal discussions
            else:
                probability += 0.05  # Far out
        except:
            pass

    # Factor 2: Contract value (higher value = higher renewal priority)
    contract_value = contract_data.get('contract_value', 0)
    if contract_value > 500000:
        probability += 0.2
    elif contract_value > 100000:
        probability += 0.15
    elif contract_value > 10000:
        probability += 0.1

    # Factor 3: Completeness of data (better data = higher confidence)
    if contract_data.get('party_1_name') and contract_data.get('party_2_name'):
        probability += 0.05

    # Factor 4: Simulated historical performance (random for demo)
    # In production, this would be based on actual renewal history
    historical_factor = random.uniform(-0.15, 0.15)
    probability += historical_factor

    # Cap between 0 and 1
    return max(0.0, min(1.0, probability))


def determine_contract_status(contract_data):
    """Determine contract status based on dates and other factors."""
    today = date.today()

    effective_date = contract_data.get('effective_date')
    expiry_date = contract_data.get('expiry_date')

    # Check effective date
    if effective_date:
        try:
            eff_date = datetime.fromisoformat(effective_date).date()
            if today < eff_date:
                return "Pending"
        except:
            pass

    # Check expiry date
    if expiry_date:
        try:
            exp_date = datetime.fromisoformat(expiry_date).date()
            if today > exp_date:
                return "Expired"
            elif (exp_date - today).days <= 30:
                return "Expiring Soon"
        except:
            pass

    return "Active"


def get_currency_from_text(text):
    """Extract currency from contract text."""
    currency_patterns = {
        'USD': r'\b(?:USD|US\$|\$|dollars?)\b',
        'EUR': r'\b(?:EUR|€|euros?)\b',
        'GBP': r'\b(?:GBP|£|pounds?)\b',
        'INR': r'\b(?:INR|₹|rupees?)\b',
        'AUD': r'\b(?:AUD|A\$)\b',
        'CAD': r'\b(?:CAD|C\$)\b',
    }

    for currency, pattern in currency_patterns.items():
        if re.search(pattern, text, re.IGNORECASE):
            return currency

    return 'USD'  # Default to USD


def analyze_contract_text(text):
    """
    Comprehensive analysis of contract text to extract analytics data.

    Returns dict with:
    - contract_value
    - currency
    - risk_indicators
    - key_terms
    """
    analysis = {
        'contract_value': extract_contract_value(text),
        'currency': get_currency_from_text(text),
        'risk_indicators': [],
        'key_terms': []
    }

    # Identify risk indicators
    risk_keywords = [
        'terminate', 'termination', 'penalty', 'liability',
        'dispute', 'arbitration', 'default', 'breach',
        'indemnify', 'warranty', 'guarantee'
    ]

    for keyword in risk_keywords:
        if re.search(r'\b' + keyword + r'\b', text, re.IGNORECASE):
            analysis['risk_indicators'].append(keyword)

    # Extract key terms (clauses)
    clause_patterns = [
        r'(?:confidentiality|non-disclosure|NDA)',
        r'(?:intellectual property|IP rights)',
        r'(?:payment terms|compensation)',
        r'(?:delivery schedule|timeline)',
        r'(?:warranty|guarantee)',
        r'(?:termination clause)',
    ]

    for pattern in clause_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            analysis['key_terms'].append(pattern.replace(r'(?:', '').replace(')', ''))

    return analysis


def get_risk_category(risk_score):
    """Convert risk score to category."""
    if risk_score <= 30:
        return "Low Risk"
    elif risk_score <= 70:
        return "Medium Risk"
    else:
        return "High Risk"


def get_risk_color(risk_score):
    """Get color code for risk visualization."""
    if risk_score <= 30:
        return "#22c55e"  # Green
    elif risk_score <= 70:
        return "#f59e0b"  # Amber
    else:
        return "#ef4444"  # Red


def format_currency(value, currency='USD'):
    """Format currency value for display."""
    if value >= 1000000:
        return f"{currency} {value/1000000:.2f}M"
    elif value >= 1000:
        return f"{currency} {value/1000:.2f}K"
    else:
        return f"{currency} {value:.2f}"


def calculate_portfolio_health(contracts_df):
    """
    Calculate overall portfolio health metrics.

    Returns:
    - total_value: Total contract value
    - avg_risk: Average risk score
    - high_risk_count: Number of high-risk contracts
    - expiring_soon: Contracts expiring in 30 days
    """
    if contracts_df.empty:
        return {
            'total_value': 0,
            'avg_risk': 0,
            'high_risk_count': 0,
            'expiring_soon': 0,
            'health_score': 0
        }

    total_value = contracts_df['contract_value'].sum()
    avg_risk = contracts_df['risk_score'].mean()
    high_risk_count = len(contracts_df[contracts_df['risk_score'] > 70])

    # Count contracts expiring soon
    today = date.today()
    expiring_soon = 0
    for expiry in contracts_df['expiry_date'].dropna():
        try:
            exp_date = datetime.fromisoformat(expiry).date()
            if 0 < (exp_date - today).days <= 30:
                expiring_soon += 1
        except:
            pass

    # Calculate health score (0-100, higher is better)
    health_score = 100
    health_score -= (avg_risk * 0.5)  # Penalize high risk
    health_score -= (high_risk_count * 5)  # Penalize high-risk contracts
    health_score -= (expiring_soon * 3)  # Penalize expiring contracts
    health_score = max(0, min(100, health_score))

    return {
        'total_value': total_value,
        'avg_risk': avg_risk,
        'high_risk_count': high_risk_count,
        'expiring_soon': expiring_soon,
        'health_score': health_score
    }
