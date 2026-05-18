import pytest
import tempfile
import shutil
import os
from pathlib import Path
import sqlite3


@pytest.fixture(scope="function")
def temp_db():
    """Create a temporary test database."""
    # Create temp database
    temp_db_path = "test_contracts.db"

    # Initialize database tables
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Create users table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'User',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP,
        is_active BOOLEAN DEFAULT 1
    )
    """)

    # Create contracts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contracts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        file_hash TEXT UNIQUE,
        file_name TEXT,
        file_path TEXT,
        file_size INTEGER,
        effective_date TEXT,
        expiry_date TEXT,
        party_1_name TEXT,
        party_2_name TEXT,
        service_type TEXT,
        payment_basis TEXT,
        user_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    )
    """)

    conn.commit()
    conn.close()

    yield temp_db_path

    # Cleanup
    if os.path.exists(temp_db_path):
        os.remove(temp_db_path)


@pytest.fixture(scope="function")
def temp_storage_dir():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "SecurePass123!",
        "role": "User"
    }


@pytest.fixture
def sample_contract_data():
    """Sample contract data for testing."""
    return {
        "file_hash": "abc123def456",
        "file_name": "test_contract.pdf",
        "file_path": "user_uploads/user_1/abc123def456.pdf",
        "file_size": 102400,
        "effective_date": "2024-01-01",
        "expiry_date": "2025-12-31",
        "party_1_name": "Company A",
        "party_2_name": "Company B",
        "service_type": "Consulting",
        "payment_basis": "Monthly",
        "user_id": 1
    }


@pytest.fixture
def sample_pdf_bytes():
    """Sample PDF file bytes for testing."""
    # Minimal valid PDF structure
    pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/Resources <<
/Font <<
/F1 <<
/Type /Font
/Subtype /Type1
/BaseFont /Helvetica
>>
>>
>>
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test Contract) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f
0000000009 00000 n
0000000058 00000 n
0000000115 00000 n
0000000317 00000 n
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
410
%%EOF"""
    return pdf_content


@pytest.fixture
def mock_streamlit_session():
    """Mock Streamlit session state."""
    return {
        "authenticated": False,
        "user": None,
        "username": None,
        "role": None,
        "user_id": None
    }
