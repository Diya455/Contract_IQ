import sqlite3
from datetime import datetime
from database.contracts_db import DB_NAME


DATE_FORMATS = [
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%d-%m-%Y",
    "%d/%m/%Y",
    "%m-%d-%Y",
    "%m/%d/%Y",
    "%d %B %Y",
    "%d %b %Y",
    "%B %d, %Y",
    "%b %d, %Y",
]


def _parse_contract_date(date_text):
    if date_text is None:
        return None

    raw = str(date_text).strip()
    if not raw:
        return None

    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        pass

    for date_format in DATE_FORMATS:
        try:
            return datetime.strptime(raw, date_format).date()
        except ValueError:
            continue

    return None


def check_expiry_alerts():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT file_name, expiry_date
        FROM contracts
        WHERE expiry_date IS NOT NULL
          AND TRIM(expiry_date) != ''
    """
    )

    rows = cursor.fetchall()
    conn.close()

    alerts = []
    today = datetime.today().date()

    for file_name, expiry_date in rows:
        expiry_date_obj = _parse_contract_date(expiry_date)
        if expiry_date_obj is None:
            alerts.append(
                {
                    "file_name": file_name,
                    "expiry_date": str(expiry_date),
                    "days_to_expiry": None,
                    "status": "date_unparsed",
                }
            )
            continue

        days_to_expiry = (expiry_date_obj - today).days

        if days_to_expiry < 0:
            status = "expired"
        elif days_to_expiry == 0:
            status = "expires_today"
        else:
            status = "upcoming"

        alerts.append(
            {
                "file_name": file_name,
                "expiry_date": expiry_date_obj.isoformat(),
                "days_to_expiry": days_to_expiry,
                "status": status,
            }
        )

    alerts.sort(
        key=lambda item: (
            item["days_to_expiry"] is None,
            item["expiry_date"],
            item["file_name"].lower(),
        )
    )
    return alerts
