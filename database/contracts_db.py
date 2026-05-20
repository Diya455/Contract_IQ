import sqlite3
import pandas as pd

DB_NAME = "contracts.db"


def init_db():
    """Initialize database with enhanced analytics fields."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Drop old table if exists (for migration)
    cursor.execute("DROP TABLE IF EXISTS contracts")

    # Create enhanced contracts table
    cursor.execute("""
    CREATE TABLE contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_hash TEXT UNIQUE,
        file_name TEXT,
        file_path TEXT,
        file_size INTEGER,

        -- Date fields
        effective_date TEXT,
        expiry_date TEXT,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        -- Party information
        party_1_name TEXT,
        party_2_name TEXT,

        -- Contract details
        service_type TEXT,
        payment_basis TEXT,
        contract_value REAL DEFAULT 0.0,
        currency TEXT DEFAULT 'USD',

        -- Analytics fields
        risk_score INTEGER DEFAULT 0,
        status TEXT DEFAULT 'Active',
        renewal_probability REAL DEFAULT 0.5,

        -- Metadata
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()


def contract_exists(file_hash):
    """Check if contract already exists."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM contracts WHERE file_hash = ?", (file_hash,))
    result = cursor.fetchone()
    conn.close()
    return result is not None


def insert_contract(data):
    """Insert a new contract with analytics fields."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
    INSERT OR IGNORE INTO contracts (
        file_hash, file_name, file_path, file_size,
        effective_date, expiry_date,
        party_1_name, party_2_name,
        service_type, payment_basis,
        contract_value, currency,
        risk_score, status, renewal_probability,
        user_id
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["file_hash"],
        data.get("file_name"),
        data.get("file_path"),
        data.get("file_size"),
        data.get("effective_date"),
        data.get("expiry_date"),
        data.get("party_1_name"),
        data.get("party_2_name"),
        data.get("service_type"),
        data.get("payment_basis"),
        data.get("contract_value", 0.0),
        data.get("currency", "USD"),
        data.get("risk_score", 0),
        data.get("status", "Active"),
        data.get("renewal_probability", 0.5),
        data.get("user_id")
    ))

    conn.commit()
    conn.close()


def get_all_contracts(user_id=None, role=None):
    """Get contracts based on user role."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        df = pd.read_sql_query(
            "SELECT * FROM contracts ORDER BY created_at DESC",
            conn
        )
    elif user_id:
        df = pd.read_sql_query(
            "SELECT * FROM contracts WHERE user_id = ? ORDER BY created_at DESC",
            conn,
            params=(user_id,)
        )
    else:
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


def update_contract_analytics(contract_id, analytics_data):
    """Update analytics fields for a contract."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    cursor.execute("""
        UPDATE contracts
        SET contract_value = ?,
            risk_score = ?,
            status = ?,
            renewal_probability = ?,
            last_modified = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (
        analytics_data.get("contract_value"),
        analytics_data.get("risk_score"),
        analytics_data.get("status"),
        analytics_data.get("renewal_probability"),
        contract_id
    ))

    conn.commit()
    conn.close()


def get_contract_by_hash(file_hash, user_id=None, role=None):
    """Get a contract by file hash with permission check."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    if role == "Admin":
        cursor.execute("SELECT * FROM contracts WHERE file_hash = ?", (file_hash,))
    elif user_id:
        cursor.execute(
            "SELECT * FROM contracts WHERE file_hash = ? AND user_id = ?",
            (file_hash, user_id)
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


def get_user_document_count(user_id):
    """Get the number of documents uploaded by a user."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM contracts WHERE user_id = ?", (user_id,))
    count = cursor.fetchone()[0]
    conn.close()
    return count


def search_contracts(query, user_id=None, role=None):
    """Search contracts by filename or party names."""
    conn = sqlite3.connect(DB_NAME)
    search_pattern = f"%{query}%"

    if role == "Admin":
        df = pd.read_sql_query("""
            SELECT * FROM contracts
            WHERE file_name LIKE ?
               OR party_1_name LIKE ?
               OR party_2_name LIKE ?
               OR service_type LIKE ?
            ORDER BY created_at DESC
        """, conn, params=(search_pattern, search_pattern, search_pattern, search_pattern))
    elif user_id:
        df = pd.read_sql_query("""
            SELECT * FROM contracts
            WHERE user_id = ?
              AND (file_name LIKE ?
                   OR party_1_name LIKE ?
                   OR party_2_name LIKE ?
                   OR service_type LIKE ?)
            ORDER BY created_at DESC
        """, conn, params=(user_id, search_pattern, search_pattern, search_pattern, search_pattern))
    else:
        df = pd.DataFrame()

    conn.close()
    return df


# ═══════════════════════════════════════════════════════════════
# ANALYTICS QUERIES
# ═══════════════════════════════════════════════════════════════

def get_total_contract_value(user_id=None, role=None):
    """Get total contract value."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    if role == "Admin":
        cursor.execute("SELECT SUM(contract_value) FROM contracts")
    elif user_id:
        cursor.execute(
            "SELECT SUM(contract_value) FROM contracts WHERE user_id = ?",
            (user_id,)
        )
    else:
        conn.close()
        return 0

    result = cursor.fetchone()[0]
    conn.close()
    return result if result else 0


def get_contracts_by_status(user_id=None, role=None):
    """Get contract counts grouped by status."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        df = pd.read_sql_query(
            "SELECT status, COUNT(*) as count FROM contracts GROUP BY status",
            conn
        )
    elif user_id:
        df = pd.read_sql_query(
            "SELECT status, COUNT(*) as count FROM contracts WHERE user_id = ? GROUP BY status",
            conn,
            params=(user_id,)
        )
    else:
        df = pd.DataFrame(columns=['status', 'count'])

    conn.close()
    return df


def get_top_parties(user_id=None, role=None, limit=10):
    """Get most frequent contracting parties."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        query = """
            SELECT party_name, COUNT(*) as count, SUM(contract_value) as total_value
            FROM (
                SELECT party_1_name as party_name, contract_value FROM contracts
                UNION ALL
                SELECT party_2_name as party_name, contract_value FROM contracts
            )
            WHERE party_name IS NOT NULL AND party_name != ''
            GROUP BY party_name
            ORDER BY count DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(limit,))
    elif user_id:
        query = """
            SELECT party_name, COUNT(*) as count, SUM(contract_value) as total_value
            FROM (
                SELECT party_1_name as party_name, contract_value FROM contracts WHERE user_id = ?
                UNION ALL
                SELECT party_2_name as party_name, contract_value FROM contracts WHERE user_id = ?
            )
            WHERE party_name IS NOT NULL AND party_name != ''
            GROUP BY party_name
            ORDER BY count DESC
            LIMIT ?
        """
        df = pd.read_sql_query(query, conn, params=(user_id, user_id, limit))
    else:
        df = pd.DataFrame(columns=['party_name', 'count', 'total_value'])

    conn.close()
    return df


def get_contracts_by_month(user_id=None, role=None):
    """Get contract counts and values by month (time series)."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        query = """
            SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count,
                SUM(contract_value) as total_value
            FROM contracts
            WHERE created_at IS NOT NULL
            GROUP BY month
            ORDER BY month
        """
        df = pd.read_sql_query(query, conn)
    elif user_id:
        query = """
            SELECT
                strftime('%Y-%m', created_at) as month,
                COUNT(*) as count,
                SUM(contract_value) as total_value
            FROM contracts
            WHERE user_id = ? AND created_at IS NOT NULL
            GROUP BY month
            ORDER BY month
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
    else:
        df = pd.DataFrame(columns=['month', 'count', 'total_value'])

    conn.close()
    return df


def get_risk_distribution(user_id=None, role=None):
    """Get distribution of contracts by risk score."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        query = """
            SELECT
                CASE
                    WHEN risk_score <= 30 THEN 'Low'
                    WHEN risk_score <= 70 THEN 'Medium'
                    ELSE 'High'
                END as risk_category,
                COUNT(*) as count,
                AVG(contract_value) as avg_value
            FROM contracts
            GROUP BY risk_category
        """
        df = pd.read_sql_query(query, conn)
    elif user_id:
        query = """
            SELECT
                CASE
                    WHEN risk_score <= 30 THEN 'Low'
                    WHEN risk_score <= 70 THEN 'Medium'
                    ELSE 'High'
                END as risk_category,
                COUNT(*) as count,
                AVG(contract_value) as avg_value
            FROM contracts
            WHERE user_id = ?
            GROUP BY risk_category
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
    else:
        df = pd.DataFrame(columns=['risk_category', 'count', 'avg_value'])

    conn.close()
    return df


def get_service_type_distribution(user_id=None, role=None):
    """Get contract distribution by service type."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        query = """
            SELECT
                service_type,
                COUNT(*) as count,
                SUM(contract_value) as total_value
            FROM contracts
            WHERE service_type IS NOT NULL AND service_type != ''
            GROUP BY service_type
            ORDER BY count DESC
        """
        df = pd.read_sql_query(query, conn)
    elif user_id:
        query = """
            SELECT
                service_type,
                COUNT(*) as count,
                SUM(contract_value) as total_value
            FROM contracts
            WHERE user_id = ? AND service_type IS NOT NULL AND service_type != ''
            GROUP BY service_type
            ORDER BY count DESC
        """
        df = pd.read_sql_query(query, conn, params=(user_id,))
    else:
        df = pd.DataFrame(columns=['service_type', 'count', 'total_value'])

    conn.close()
    return df


def get_expiring_contracts(days=30, user_id=None, role=None):
    """Get contracts expiring within specified days."""
    conn = sqlite3.connect(DB_NAME)

    if role == "Admin":
        query = """
            SELECT *
            FROM contracts
            WHERE expiry_date IS NOT NULL
            AND DATE(expiry_date) BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')
            ORDER BY expiry_date
        """
        df = pd.read_sql_query(query, conn, params=(days,))
    elif user_id:
        query = """
            SELECT *
            FROM contracts
            WHERE user_id = ?
            AND expiry_date IS NOT NULL
            AND DATE(expiry_date) BETWEEN DATE('now') AND DATE('now', '+' || ? || ' days')
            ORDER BY expiry_date
        """
        df = pd.read_sql_query(query, conn, params=(user_id, days))
    else:
        df = pd.DataFrame()

    conn.close()
    return df
