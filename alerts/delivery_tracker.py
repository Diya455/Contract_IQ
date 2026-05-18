import sqlite3
from datetime import datetime
from database.contracts_db import DB_NAME

def check_delivery_status():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT id, expected_delivery, actual_delivery
    FROM contracts
    WHERE expected_delivery IS NOT NULL
    """)

    rows = cursor.fetchall()
    results = []

    for contract_id, expected, actual in rows:
        expected = datetime.fromisoformat(expected)

        if actual:
            actual = datetime.fromisoformat(actual)
            if actual > expected:
                results.append((contract_id, "Delayed"))
            else:
                results.append((contract_id, "On-Time"))
        else:
            if datetime.today() > expected:
                results.append((contract_id, "Delayed"))
    
    conn.close()
    return results
