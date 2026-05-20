import pytest
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from auth.authenticator import hash_password, verify_password


class TestAuthenticator:
    """Test suite for authentication functions."""

    def test_hash_password(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        assert hashed is not None
        assert isinstance(hashed, str)
        assert len(hashed) > 50  # Bcrypt hashes are ~60 chars
        assert hashed != password  # Should be hashed, not plain

    def test_hash_password_different_hashes(self):
        """Test that same password produces different hashes (salt)."""
        password = "SecurePassword123!"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        assert hash1 != hash2  # Different salts

    def test_verify_password_correct(self):
        """Test password verification with correct password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        result = verify_password(password, hashed)

        assert result is True

    def test_verify_password_incorrect(self):
        """Test password verification with incorrect password."""
        password = "SecurePassword123!"
        wrong_password = "WrongPassword456!"
        hashed = hash_password(password)

        result = verify_password(wrong_password, hashed)

        assert result is False

    def test_verify_password_empty_string(self):
        """Test password verification with empty password."""
        password = "SecurePassword123!"
        hashed = hash_password(password)

        result = verify_password("", hashed)

        assert result is False

    def test_hash_password_special_characters(self):
        """Test hashing passwords with special characters."""
        password = "P@ssw0rd!#$%^&*()"
        hashed = hash_password(password)

        assert hashed is not None
        result = verify_password(password, hashed)
        assert result is True

    def test_hash_password_unicode(self):
        """Test hashing passwords with unicode characters."""
        password = "Пароль123测试"
        hashed = hash_password(password)

        assert hashed is not None
        result = verify_password(password, hashed)
        assert result is True

    def test_verify_password_case_sensitive(self):
        """Test that password verification is case-sensitive."""
        password = "SecurePassword"
        hashed = hash_password(password)

        result1 = verify_password("securepassword", hashed)
        result2 = verify_password("SECUREPASSWORD", hashed)

        assert result1 is False
        assert result2 is False

    def test_hash_password_long_password(self):
        """Test hashing very long passwords."""
        password = "a" * 200
        hashed = hash_password(password)

        assert hashed is not None
        result = verify_password(password, hashed)
        assert result is True


class TestAuthenticationIntegration:
    """Integration tests for authentication flow."""

    def setup_method(self):
        """Setup test database."""
        import database.users_db as users_db
        users_db.DB_NAME = "test_contracts.db"
        users_db.init_users_table()

    def teardown_method(self):
        """Cleanup test database."""
        if os.path.exists("test_contracts.db"):
            os.remove("test_contracts.db")

    def test_register_and_login_flow(self):
        """Test complete registration and login flow."""
        from auth.authenticator import register_user, login_user

        username = "testuser"
        email = "test@example.com"
        password = "SecurePass123!"

        # Register user
        result = register_user(username, email, password)
        assert result is True

        # Login with correct credentials
        user = login_user(username, password)
        assert user is not None
        assert user["username"] == username
        assert user["email"] == email

    def test_login_with_wrong_password(self):
        """Test login fails with wrong password."""
        from auth.authenticator import register_user, login_user

        username = "testuser"
        email = "test@example.com"
        password = "SecurePass123!"

        # Register user
        register_user(username, email, password)

        # Try to login with wrong password
        user = login_user(username, "WrongPassword!")
        assert user is None

    def test_login_nonexistent_user(self):
        """Test login fails for non-existent user."""
        from auth.authenticator import login_user

        user = login_user("nonexistent", "password")
        assert user is None

    def test_register_duplicate_username(self):
        """Test registration fails with duplicate username."""
        from auth.authenticator import register_user

        username = "testuser"

        # Register first user
        result1 = register_user(username, "user1@test.com", "pass123")
        assert result1 is True

        # Try to register with same username
        result2 = register_user(username, "user2@test.com", "pass456")
        assert result2 is False

    def test_register_duplicate_email(self):
        """Test registration fails with duplicate email."""
        from auth.authenticator import register_user

        email = "test@example.com"

        # Register first user
        result1 = register_user("user1", email, "pass123")
        assert result1 is True

        # Try to register with same email
        result2 = register_user("user2", email, "pass456")
        assert result2 is False

    def test_login_updates_last_login(self):
        """Test that login updates last_login timestamp."""
        from auth.authenticator import register_user, login_user
        import database.users_db as users_db

        username = "testuser"
        email = "test@example.com"
        password = "SecurePass123!"

        # Register and login
        register_user(username, email, password)
        user = login_user(username, password)

        # Check that last_login was updated
        user_data = users_db.get_user_by_username(username)
        assert user_data["last_login"] is not None
