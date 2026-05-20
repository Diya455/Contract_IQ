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

# Same pattern but with a unique group name to avoid conflicts when used twice in one regex
DATE_CAPTURE_EXPIRY = (
    r"(?P<date2>"
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
        r"Between\s+(.+?)\s+and",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return "Unknown"


def extract_contract_dates(text):
    dates = re.findall(DATE_CAPTURE, text)
    parsed_dates = []

    for date_text in dates:
        parsed_date = _parse_date_string(date_text)
        if parsed_date:
            parsed_dates.append(parsed_date)

    start_date = parsed_dates[0] if len(parsed_dates) >= 1 else None
    end_date   = parsed_dates[1] if len(parsed_dates) >= 2 else None

    return start_date, end_date


def _extract_effective_date(text, start_date):
    """
    Try explicit keyword patterns first, fall back to first parsed date.
    """
    effective_match = re.search(
        rf"(?:Effective Date|Commencement Date|Start Date|Made effective as of|"
        rf"entered into as of|made as of|effective as of)"
        rf"[^A-Za-z0-9]*{DATE_CAPTURE}",
        text,
        re.IGNORECASE,
    )
    if effective_match:
        dt = _parse_date_string(effective_match.group("date"))
        if dt:
            return dt.strftime("%Y-%m-%d")

    if start_date:
        return start_date.strftime("%Y-%m-%d")

    return None


def _extract_expiry_date(text, end_date):
    """
    Try explicit keyword patterns first, then natural-language phrases,
    then fall back to the second parsed date in the document.
    """
    # 1. Explicit label patterns  e.g. "Expiry Date: 31 December 2025"
    explicit_match = re.search(
        rf"(?:Expiry Date|Expiration Date|Termination Date|Term End Date|"
        rf"End Date|Expires On|Terminates On)"
        rf"[^A-Za-z0-9]*{DATE_CAPTURE}",
        text,
        re.IGNORECASE,
    )
    if explicit_match:
        dt = _parse_date_string(explicit_match.group("date"))
        if dt:
            return dt.strftime("%Y-%m-%d")

    # 2. Natural-language phrases  e.g. "shall expire on December 31, 2025"
    #    or "remain in effect until 31 December 2026"
    natural_match = re.search(
        rf"(?:shall\s+expire\s+on|"
        rf"expire[sd]?\s+on|"
        rf"remain[s]?\s+in\s+effect\s+until|"
        rf"in\s+effect\s+until|"
        rf"valid\s+until|"
        rf"valid\s+through|"
        rf"through\s+and\s+including|"
        rf"shall\s+terminate\s+on|"
        rf"terminate[sd]?\s+on|"
        rf"concludes?\s+on|"
        rf"ends?\s+on)"
        rf"\s+{DATE_CAPTURE_EXPIRY}",
        text,
        re.IGNORECASE,
    )
    if natural_match:
        dt = _parse_date_string(natural_match.group("date2"))
        if dt:
            return dt.strftime("%Y-%m-%d")

    # 3. Fallback: second date found anywhere in the document
    if end_date:
        return end_date.strftime("%Y-%m-%d")

    return None


def _extract_party_names(text):
    """
    Try multiple party-name patterns in order of specificity.
    Returns (party_1_name, party_2_name).
    """
    party_1 = None
    party_2 = None

    # Pattern 1: "Party 1: <name>" / "Party 2: <name>"
    p1_match = re.search(r"Party\s*1\s*:\s*([A-Za-z0-9\s,\.&]+?)(?:\n|\(|and\s+Party)", text, re.IGNORECASE)
    p2_match = re.search(r"Party\s*2\s*:\s*([A-Za-z0-9\s,\.&]+?)(?:\n|\(|for\s+the)", text, re.IGNORECASE)
    if p1_match:
        party_1 = p1_match.group(1).strip().rstrip(",")
    if p2_match:
        party_2 = p2_match.group(1).strip().rstrip(",")
    if party_1 and party_2:
        return party_1, party_2

    # Pattern 2: "between <Party1> (the..." or "between <Party1>, a ..."
    between_match = re.search(
        r"between\s+([A-Za-z0-9\s,\.&]+?)\s*(?:\(|,\s*a\s|\bhereinafter\b)",
        text,
        re.IGNORECASE,
    )
    if between_match:
        party_1 = between_match.group(1).strip()

    # Pattern 3: "and <Party2> (the..." following the between clause
    and_match = re.search(
        r"\band\s+([A-Za-z0-9\s,\.&]+?)\s*(?:\(|,\s*a\s|\bhereinafter\b)",
        text,
        re.IGNORECASE,
    )
    if and_match:
        party_2 = and_match.group(1).strip()
    if party_1 and party_2:
        return party_1, party_2

    # Pattern 4: plain "between X and Y" with a word-boundary stop
    plain_match = re.search(
        r"between\s+([A-Za-z0-9][\w\s\.,&]*?)\s+and\s+([A-Za-z0-9][\w\s\.,&]*?)(?:\s+for|\s+the|\s+regarding|\.|,|$)",
        text,
        re.IGNORECASE,
    )
    if plain_match:
        party_1 = party_1 or plain_match.group(1).strip()
        party_2 = party_2 or plain_match.group(2).strip()

    return party_1, party_2


def _extract_service_type(text):
    """
    Match service type keywords — transportation-specific first,
    then generic professional service categories.
    """
    service_map = [
        # Transportation / logistics (original)
        (r"\bFirm Service\b",                    "Firm Service"),
        (r"\bInterruptible Service\b",            "Interruptible Service"),
        (r"\bRoad Transportation\b",              "Road Transportation"),
        (r"\bTransportation Services Agreement\b","Transportation Services"),
        (r"\bFreight\b",                          "Freight Service"),
        (r"\bLogistics\b",                        "Logistics Service"),
        # General professional services
        (r"\bConsulting\b",                       "Consulting Services"),
        (r"\bConsultancy\b",                      "Consulting Services"),
        (r"\bSoftware\b",                         "Software Services"),
        (r"\bSaaS\b",                             "SaaS Services"),
        (r"\bMaintenance\b",                      "Maintenance Services"),
        (r"\bSupport Services\b",                 "Support Services"),
        (r"\bProcurement\b",                      "Procurement Services"),
        (r"\bStaffing\b",                         "Staffing Services"),
        (r"\bMarketing\b",                        "Marketing Services"),
        (r"\bLegal Services\b",                   "Legal Services"),
        (r"\bAudit\b",                            "Audit Services"),
        (r"\bConstruction\b",                     "Construction Services"),
    ]
    for pattern, label in service_map:
        if re.search(pattern, text, re.IGNORECASE):
            return label

    return "General Services"


def _extract_payment_basis(text):
    """
    Match payment basis keywords — specific first, generic fallback.
    """
    payment_map = [
        # Transportation-specific (original)
        (r"\bTariff\b",                  "Tariff Based"),
        (r"\bcarload rate\b",            "Carload Rate"),
        (r"\bDedicated Rates?\b",        "Dedicated Rate"),
        (r"\btransportation fee\b",      "Transportation Fee"),
        # Generic payment terms
        (r"\bMonthly\b",                 "Monthly"),
        (r"\bAnnual(?:ly)?\b",           "Annual"),
        (r"\bQuarterly\b",               "Quarterly"),
        (r"\bFixed\s+(?:Fee|Price)\b",   "Fixed Fee"),
        (r"\bHourly\b",                  "Hourly Rate"),
        (r"\bMilestone\b",               "Milestone Based"),
        (r"\bRetainer\b",                "Retainer"),
        (r"\bSubscription\b",            "Subscription"),
        (r"\bInvoice\b",                 "Invoice Based"),
        (r"\bPer\s+Diem\b",              "Per Diem"),
        (r"\bTime\s+and\s+Materials?\b", "Time & Materials"),
    ]
    for pattern, label in payment_map:
        if re.search(pattern, text, re.IGNORECASE):
            return label

    return "As Per Agreement"


def extract_structured_data(text):
    """
    Main extraction function. Returns a dict with all structured fields.
    """
    start_date, end_date = extract_contract_dates(text)

    effective_date = _extract_effective_date(text, start_date)
    expiry_date    = _extract_expiry_date(text, end_date)
    party_1_name, party_2_name = _extract_party_names(text)
    service_type   = _extract_service_type(text)
    payment_basis  = _extract_payment_basis(text)

    return {
        "effective_date": effective_date,
        "expiry_date":    expiry_date,
        "party_1_name":   party_1_name,
        "party_2_name":   party_2_name,
        "service_type":   service_type,
        "payment_basis":  payment_basis,
    }
