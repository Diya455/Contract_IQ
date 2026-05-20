import pytest
import sqlite3
import sys
import os
import gc
import bcrypt

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import database.users_db as users_db


class TestUsersDatabase:
    """Test suite for user database operations."""

    def setup_method(self):
        """Setup test database before each test."""
        users_db.DB_NAME = "test_contracts.db"
        users_db.init_users_table()

    def teardown_method(self):
        """Cleanup test database after each test."""
        gc.collect()
        if os.path.exists("test_contracts.db"):
            try:
                os.remove("test_contracts.db")
            except PermissionError:
                pass

    # ─────────────────────────────────────────────────────────────────────────
    # Table initialisation
    # ─────────────────────────────────────────────────────────────────────────

    def test_init_users_table(self):
        """Test user table creation."""
        users_db.init_users_table()

        conn = sqlite3.connect(users_db.DB_NAME)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        )
        result = cursor.fetchone()
        conn.close()

        assert result is not None
        assert result[0] == "users"

    # ─────────────────────────────────────────────────────────────────────────
    # Create user
    # ─────────────────────────────────────────────────────────────────────────

    def test_create_user_success(self, sample_user_data):
        """Test creating a new user successfully."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        result = users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        assert result is True

    def test_create_user_duplicate_username(self, sample_user_data):
        """Test creating user with duplicate username fails."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        result = users_db.create_user(
            sample_user_data["username"],   # same username
            "different@example.com",
            password_hash,
            sample_user_data["role"],
        )

        assert result is False

    def test_create_user_duplicate_email(self, sample_user_data):
        """Test creating user with duplicate email fails."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        result = users_db.create_user(
            "differentuser",
            sample_user_data["email"],  # same email
            password_hash,
            sample_user_data["role"],
        )

        assert result is False

    # ─────────────────────────────────────────────────────────────────────────
    # Get user
    # ─────────────────────────────────────────────────────────────────────────

    def test_get_user_by_username_exists(self, sample_user_data):
        """Test retrieving user by username."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        user = users_db.get_user_by_username(sample_user_data["username"])

        assert user is not None
        assert user["username"] == sample_user_data["username"]
        assert user["email"] == sample_user_data["email"]
        assert user["role"] == sample_user_data["role"]
        assert user["is_active"] == 1

    def test_get_user_by_username_not_exists(self):
        """Test retrieving non-existent user returns None."""
        user = users_db.get_user_by_username("nonexistent")
        assert user is None

    def test_get_user_by_email_exists(self, sample_user_data):
        """Test retrieving user by email."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        user = users_db.get_user_by_email(sample_user_data["email"])

        assert user is not None
        assert user["email"] == sample_user_data["email"]

    # ─────────────────────────────────────────────────────────────────────────
    # Update last login
    # ─────────────────────────────────────────────────────────────────────────

    def test_update_last_login(self, sample_user_data):
        """Test updating user's last login timestamp."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            sample_user_data["role"],
        )

        user = users_db.get_user_by_username(sample_user_data["username"])
        user_id = user["id"]

        users_db.update_last_login(user_id)

        updated_user = users_db.get_user_by_id(user_id)
        assert updated_user["last_login"] is not None

    # ─────────────────────────────────────────────────────────────────────────
    # Get all users  — isolated DB to avoid bleedover from other tests
    # ─────────────────────────────────────────────────────────────────────────

    def test_get_all_users(self, sample_user_data, tmp_path, monkeypatch):
        """Test retrieving all users."""
        monkeypatch.setattr(users_db, "DB_NAME", str(tmp_path / "users.db"))
        users_db.init_users_table()

        hashed = bcrypt.hashpw(b"pass", bcrypt.gensalt()).decode()

        users_db.create_user("user1", "user1@test.com", hashed, "User")
        users_db.create_user("user2", "user2@test.com", hashed, "User")
        users_db.create_user("admin1", "admin1@test.com", hashed, "Admin")

        users = users_db.get_all_users()
        assert len(users) == 3

    # ─────────────────────────────────────────────────────────────────────────
    # Deactivate / activate  — isolated DB to avoid bleedover
    # ─────────────────────────────────────────────────────────────────────────

    def test_deactivate_user(self, sample_user_data, tmp_path, monkeypatch):
        """Test deactivating a user."""
        monkeypatch.setattr(users_db, "DB_NAME", str(tmp_path / "users.db"))
        users_db.init_users_table()

        hashed = bcrypt.hashpw(
            sample_user_data["password"].encode(), bcrypt.gensalt()
        ).decode()

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            hashed,
            sample_user_data["role"],
        )

        user = users_db.get_user_by_username(sample_user_data["username"])
        result = users_db.deactivate_user(user["id"])
        assert result is True

        # Deactivated user should not be returned by get_user_by_username
        deactivated = users_db.get_user_by_username(sample_user_data["username"])
        assert deactivated is None

    def test_activate_user(self, sample_user_data, tmp_path, monkeypatch):
        """Test activating a deactivated user."""
        monkeypatch.setattr(users_db, "DB_NAME", str(tmp_path / "users.db"))
        users_db.init_users_table()

        hashed = bcrypt.hashpw(
            sample_user_data["password"].encode(), bcrypt.gensalt()
        ).decode()

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            hashed,
            sample_user_data["role"],
        )

        user = users_db.get_user_by_username(sample_user_data["username"])
        user_id = user["id"]

        users_db.deactivate_user(user_id)
        result = users_db.activate_user(user_id)
        assert result is True

        # User should be retrievable again after activation
        active_user = users_db.get_user_by_username(sample_user_data["username"])
        assert active_user is not None

    # ─────────────────────────────────────────────────────────────────────────
    # Update role
    # ─────────────────────────────────────────────────────────────────────────

    def test_update_user_role(self, sample_user_data):
        """Test updating user role."""
        password_hash = bcrypt.hashpw(
            sample_user_data["password"].encode("utf-8"), bcrypt.gensalt()
        ).decode("utf-8")

        users_db.create_user(
            sample_user_data["username"],
            sample_user_data["email"],
            password_hash,
            "User",
        )

        user = users_db.get_user_by_username(sample_user_data["username"])
        user_id = user["id"]

        result = users_db.update_user_role(user_id, "Admin")
        assert result is True

        updated_user = users_db.get_user_by_id(user_id)
        assert updated_user["role"] == "Admin"
