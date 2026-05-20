import bcrypt
import pytest
import sqlite3
import sys
import os
import pandas as pd
import bcrypt

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from database import users_db
from database import users_db
import database.contracts_db as contracts_db


class TestContractsDatabase:
    """Test suite for contracts database operations."""

    def setup_method(self):
        """Setup test database before each test."""
        contracts_db.DB_NAME = "test_contracts.db"
        contracts_db.init_db()

    def teardown_method(self):
        """Cleanup test database after each test."""
        if os.path.exists("test_contracts.db"):
            os.remove("test_contracts.db")

    def test_init_db(self):
        """Test database initialization."""
        contracts_db.init_db()

        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()

        # Check if table exists
        cursor.execute("""
            SELECT name FROM sqlite_master
            WHERE type='table' AND name='contracts'
        """)
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "contracts"

    def test_insert_contract(self, sample_contract_data):
        """Test inserting a contract."""
        contracts_db.insert_contract(sample_contract_data)

        # Verify contract was inserted
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        result = cursor.fetchone()
        conn.close()

        assert result is not None

    def test_insert_duplicate_contract(self, sample_contract_data):
        """Test inserting duplicate contract (should be ignored)."""
        # Insert first time
        contracts_db.insert_contract(sample_contract_data)

        # Try to insert again
        contracts_db.insert_contract(sample_contract_data)

        # Count contracts with same hash
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        count = cursor.fetchone()[0]
        conn.close()

        assert count == 1

    def test_contract_exists_true(self, sample_contract_data):
        """Test checking if contract exists (true case)."""
        contracts_db.insert_contract(sample_contract_data)

        exists = contracts_db.contract_exists(sample_contract_data["file_hash"])
        assert exists is True

    def test_contract_exists_false(self):
        """Test checking if contract exists (false case)."""
        exists = contracts_db.contract_exists("nonexistent_hash")
        assert exists is False

    def test_get_all_contracts_for_user(self, sample_contract_data):
        """Test retrieving contracts for specific user."""
        # Insert contract for user 1
        sample_contract_data["user_id"] = 1
        contracts_db.insert_contract(sample_contract_data)

        # Insert another contract for user 2
        contract_2 = sample_contract_data.copy()
        contract_2["file_hash"] = "xyz789"
        contract_2["user_id"] = 2
        contracts_db.insert_contract(contract_2)

        # Get contracts for user 1
        df = contracts_db.get_all_contracts(user_id=1, role="User")

        assert len(df) == 1
        assert df.iloc[0]["user_id"] == 1

    def test_get_all_users(self, sample_user_data, tmp_path, monkeypatch):
        hashed_pw = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode()
        monkeypatch.setattr(users_db, "DB_NAME", str(tmp_path / "users.db"))
        users_db.init_users_table()

        users_db.create_user("user1", "user1@test.com", hashed_pw, "User")
        users_db.create_user("user2", "user2@test.com", hashed_pw, "User")
        users_db.create_user("admin1", "admin1@test.com", hashed_pw, "Admin")

        users = users_db.get_all_users()
        assert len(users) == 3

    def test_get_all_contracts_for_admin(self, sample_contract_data):
        """Test that admin can see all contracts."""
        # Insert contracts for different users
        sample_contract_data["user_id"] = 1
        contracts_db.insert_contract(sample_contract_data)

        contract_2 = sample_contract_data.copy()
        contract_2["file_hash"] = "xyz789"
        contract_2["user_id"] = 2
        contracts_db.insert_contract(contract_2)

        # Get contracts as admin
        df = contracts_db.get_all_contracts(user_id=1, role="Admin")

        assert len(df) == 2

    def test_get_contract_by_id_success(self, sample_contract_data):
        """Test retrieving contract by ID."""
        contracts_db.insert_contract(sample_contract_data)

        # Get the contract ID
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        contract_id = cursor.fetchone()[0]
        conn.close()

        # Retrieve contract
        contract = contracts_db.get_contract_by_id(contract_id, user_id=1, role="User")

        assert contract is not None
        assert contract["file_name"] == sample_contract_data["file_name"]

    def test_get_contract_by_id_wrong_user(self, sample_contract_data):
        """Test user cannot access other user's contract."""
        sample_contract_data["user_id"] = 1
        contracts_db.insert_contract(sample_contract_data)

        # Get the contract ID
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        contract_id = cursor.fetchone()[0]
        conn.close()

        # Try to retrieve as different user
        contract = contracts_db.get_contract_by_id(contract_id, user_id=2, role="User")

        assert contract is None

    def test_get_contract_by_hash(self, sample_contract_data):
        """Test retrieving contract by file hash."""
        contracts_db.insert_contract(sample_contract_data)

        contract = contracts_db.get_contract_by_hash(
            sample_contract_data["file_hash"],
            user_id=1,
            role="User"
        )

        assert contract is not None
        assert contract["file_hash"] == sample_contract_data["file_hash"]

    def test_delete_contract_success(self, sample_contract_data):
        """Test deleting a contract."""
        contracts_db.insert_contract(sample_contract_data)

        # Get the contract ID
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        contract_id = cursor.fetchone()[0]
        conn.close()

        # Delete contract
        result = contracts_db.delete_contract(contract_id, user_id=1, role="User")

        assert result is True

        # Verify it's deleted
        contract = contracts_db.get_contract_by_id(contract_id, user_id=1, role="User")
        assert contract is None

    def test_delete_contract_wrong_user(self, sample_contract_data):
        """Test user cannot delete other user's contract."""
        sample_contract_data["user_id"] = 1
        contracts_db.insert_contract(sample_contract_data)

        # Get the contract ID
        conn = sqlite3.connect(contracts_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM contracts WHERE file_hash = ?",
                      (sample_contract_data["file_hash"],))
        contract_id = cursor.fetchone()[0]
        conn.close()

        # Try to delete as different user
        result = contracts_db.delete_contract(contract_id, user_id=2, role="User")

        assert result is False

    def test_get_user_document_count(self, sample_contract_data):
        """Test counting documents for a user."""
        # Insert multiple contracts for user 1
        sample_contract_data["user_id"] = 1
        contracts_db.insert_contract(sample_contract_data)

        contract_2 = sample_contract_data.copy()
        contract_2["file_hash"] = "xyz789"
        contracts_db.insert_contract(contract_2)

        # Insert contract for user 2
        contract_3 = sample_contract_data.copy()
        contract_3["file_hash"] = "abc999"
        contract_3["user_id"] = 2
        contracts_db.insert_contract(contract_3)

        # Count for user 1
        count = contracts_db.get_user_document_count(1)

        assert count == 2

    def test_search_contracts_by_filename(self, sample_contract_data):
        """Test searching contracts by filename."""
        contracts_db.insert_contract(sample_contract_data)

        # Search by partial filename
        df = contracts_db.search_contracts("test", user_id=1, role="User")

        assert len(df) > 0
        assert "test" in df.iloc[0]["file_name"].lower()

    def test_search_contracts_by_party_name(self, sample_contract_data):
        """Test searching contracts by party name."""
        contracts_db.insert_contract(sample_contract_data)

        # Search by party name
        df = contracts_db.search_contracts("Company A", user_id=1, role="User")

        assert len(df) > 0
        assert "Company A" in df.iloc[0]["party_1_name"]

    def test_search_contracts_no_results(self, sample_contract_data):
        """Test searching with no results."""
        contracts_db.insert_contract(sample_contract_data)

        df = contracts_db.search_contracts("nonexistent", user_id=1, role="User")

        assert len(df) == 0
