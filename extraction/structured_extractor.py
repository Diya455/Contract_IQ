import re
from datetime import datetime


DATE_CAPTURE = (
    r"(?P<date>"
    r"\d{1,2}\s+[A-Za-z]+\s+\d{4}|"
    r"[A-Za-z]+\s+\d{1,2},\s*\d{4}|"
    r"\d{4}-\d{2}-\d{2}|"
    r"\d{1,2}[/-]\d{1,2}[/-]\d{4}"
    r")"
)

DATE_FORMATS = [
    "%Y-%m-%d",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%m/%d/%Y",
    "%m-%d-%Y",
]


def _parse_date_string(date_text):
    if not date_text:
        return None

    clean_date = date_text.strip().strip(".,;:)")

    try:
        return datetime.fromisoformat(clean_date)
    except ValueError:
        pass

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(clean_date, date_format)
        except ValueError:
            continue

    return None


def extract_vendor_name(text):
    patterns = [
        r"Vendor\s*:\s*(.+)",
        r"Supplier\s*:\s*(.+)",
        r"Between\s+(.+?)\s+and"
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Unknown"

def extract_contract_dates(text):
    date_pattern = DATE_CAPTURE

    dates = re.findall(date_pattern, text)
    parsed_dates = []

    for date_text in dates:
        parsed_date = _parse_date_string(date_text)
        if parsed_date:
            parsed_dates.append(parsed_date)

    start_date = None
    end_date = None

    if len(parsed_dates) >= 1:
        start_date = parsed_dates[0]

    if len(parsed_dates) >= 2:
        end_date = parsed_dates[1]
    return start_date, end_date

def extract_structured_data(text):

    start_date, end_date = extract_contract_dates(text)

    effective_date = None

    effective_match = re.search(
        rf"(?:Effective Date|Commencement Date|Start Date)[^A-Za-z0-9]*{DATE_CAPTURE}",
        text,
        re.IGNORECASE
    )

    if effective_match:
        effective_dt = _parse_date_string(effective_match.group("date"))
        if effective_dt:
            effective_date = effective_dt.strftime("%Y-%m-%d")

    if not effective_date and start_date:
        effective_date = start_date.strftime("%Y-%m-%d")

    expiry_date = None
    expiry_match = re.search(
        rf"(?:Expiry Date|Expiration Date|Termination Date|Term End Date|End Date|Expires On|Terminates On)[^A-Za-z0-9]*{DATE_CAPTURE}",
        text,
        re.IGNORECASE
    )

    if expiry_match:
        expiry_dt = _parse_date_string(expiry_match.group("date"))
        if expiry_dt:
            expiry_date = expiry_dt.strftime("%Y-%m-%d")

    if not expiry_date and end_date:
        expiry_date = end_date.strftime("%Y-%m-%d")

    party_1_name = None
    party_2_name = None

    between_match = re.search(
        r'between\s+(.*?)\s+(?:,|\()',
        text,
        re.IGNORECASE
    )
    and_match = re.search(
        r'and\s+(.*?)\s+(?:,|\()',
        text,
        re.IGNORECASE
    )

    if between_match:
        party_1_name = between_match.group(1).strip()

    if and_match:
        party_2_name = and_match.group(1).strip()
    if "Firm Service" in text:
        service_type = "Firm Service"
    elif "Interruptible Service" in text:
        service_type = "Interruptible Service"
    elif "Road Transportation" in text:
        service_type = "Road Transportation"
    elif "Transportation Services Agreement" in text:
        service_type = "Transportation Services"
    else:
        service_type = "Transportation"

    if "Tariff" in text:
        payment_basis = "Tariff Based"
    elif "carload rate" in text.lower():
        payment_basis = "Carload Rate"
    elif "Dedicated Rates" in text:
        payment_basis = "Dedicated Rate"
    elif "transportation fee" in text.lower():
        payment_basis = "Transportation Fee"
    else:
        payment_basis = "As Per Agreement"


    return {
    "effective_date": effective_date,
    "expiry_date": expiry_date,
    "party_1_name": party_1_name,
    "party_2_name": party_2_name,
    "service_type": service_type,
    "payment_basis": payment_basis
}
