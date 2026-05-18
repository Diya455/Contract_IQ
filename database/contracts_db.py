import sqlite3
import pandas as pd

DB_NAME = "contracts.db"


def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("DROP TABLE IF EXISTS contracts")

    cursor.execute("""
    CREATE TABLE contracts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    file_hash TEXT UNIQUE,
    file_name TEXT,

    effective_date TEXT,
    expiry_date TEXT,

    party_1_name TEXT,
    party_2_name TEXT,
    service_type TEXT,
    payment_basis TEXT,

    user_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (user_id) REFERENCES users(id)
)""")

    conn.commit()
    conn.close()

def contract_exists(file_hash):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("SELECT 1 FROM contracts WHERE file_hash = ?", (file_hash,))
    result = cursor.fetchone()

    conn.close()
    return result is not None

def insert_contract(data):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO contracts (
    file_hash,
    file_name,
    effective_date,
    expiry_date,
    party_1_name,
    party_2_name,
    service_type,
    payment_basis,
    user_id
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
    data["file_hash"],
    data.get("file_name"),
    data.get("effective_date"),
    data.get("expiry_date"),
    data.get("party_1_name"),
    data.get("party_2_name"),
    data.get("service_type"),
    data.get("payment_basis"),
    data.get("user_id")
))

    conn.commit()
    conn.close()

def get_all_contracts(user_id=None, role=None):
    """
    Get contracts based on user role.
    Admins see all contracts, regular users see only their own.
    """
    conn = sqlite3.connect(DB_NAME)
    
    if role == "Admin":
        # Admins see all contracts
        df = pd.read_sql_query("SELECT * FROM contracts", conn)
    elif user_id:
        # Regular users see only their contracts
        df = pd.read_sql_query(
            "SELECT * FROM contracts WHERE user_id = ?", 
            conn, 
            params=(user_id,)
        )
    else:
        # No user specified, return empty
        df = pd.DataFrame()
    
    conn.close()
    return df

def get_contract_by_id(contract_id, user_id=None, role=None):
    """Get a specific contract by ID with permission check."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    if role == "Admin":
        cursor.execute("SELECT * FROM contracts WHERE id = ?", (contract_id,))
    elif user_id:
        cursor.execute(
            "SELECT * FROM contracts WHERE id = ? AND user_id = ?", 
            (contract_id, user_id)
        )
    else:
        conn.close()
        return None
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def delete_contract(contract_id, user_id=None, role=None):
    """Delete a contract with permission check."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        if role == "Admin":
            cursor.execute("DELETE FROM contracts WHERE id = ?", (contract_id,))
        elif user_id:
            cursor.execute(
                "DELETE FROM contracts WHERE id = ? AND user_id = ?", 
                (contract_id, user_id)
            )
        else:
            conn.close()
            return False
        
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    except Exception:
        return False