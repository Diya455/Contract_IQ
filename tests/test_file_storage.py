import pytest
import sys
import os
from pathlib import Path
import tempfile
import shutil

# Add parent directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Try to import storage module, skip tests if not available
try:
    import storage.file_storage as file_storage
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False

# Skip all tests in this file if storage module not available
pytestmark = pytest.mark.skipif(
    not STORAGE_AVAILABLE,
    reason="Storage module not implemented yet. Copy storage/ files to enable these tests."
)


class TestFileStorage:
    """Test suite for file storage operations."""

    def setup_method(self):
        """Setup test storage directory."""
        if not STORAGE_AVAILABLE:
            pytest.skip("Storage module not available")
        self.temp_dir = tempfile.mkdtemp()
        file_storage.UPLOAD_DIR = self.temp_dir

    def teardown_method(self):
        """Cleanup test storage directory."""
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_init_storage(self):
        """Test storage directory initialization."""
        file_storage.init_storage()

        assert os.path.exists(self.temp_dir)
        assert os.path.isdir(self.temp_dir)

    def test_get_user_storage_path(self):
        """Test getting user-specific storage path."""
        user_id = 1
        user_path = file_storage.get_user_storage_path(user_id)

        assert user_path.exists()
        assert user_path.is_dir()
        assert "user_1" in str(user_path)

    def test_save_uploaded_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_storage, "STORAGE_BASE_DIR", str(tmp_path))
        file_path = file_storage.save_uploaded_file(
            user_id=1,
            file_hash="abc123",
            file_name="test.pdf",
            file_bytes=b"Test PDF content"
        )
        assert file_path is not None

    def test_get_file_size(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_storage, "STORAGE_BASE_DIR", str(tmp_path))
        file_bytes = b"Test PDF content"
        file_path = file_storage.save_uploaded_file(1, "abc123", "test.pdf", file_bytes)
        assert file_storage.get_file_size(file_path) == len(file_bytes)

    def test_delete_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(file_storage, "STORAGE_BASE_DIR", str(tmp_path))
        file_path = file_storage.save_uploaded_file(1, "abc123", "test.pdf", b"content")
        assert file_storage.delete_file(file_path) is True

    def test_get_user_storage_usage_empty(self):
        """Test storage usage for user with no files."""
        user_id = 1
        usage = file_storage.get_user_storage_usage(user_id)

        assert usage["total_bytes"] == 0
        assert usage["total_mb"] == 0
        assert usage["file_count"] == 0

    def test_check_storage_quota_under_limit(self):
        """Test storage quota check when under limit."""
        user_id = 1
        new_file_size = 1024 * 1024  # 1 MB

        can_upload, message = file_storage.check_storage_quota(user_id, new_file_size)

        assert can_upload is True
        assert message == "OK"

    def test_format_file_size_bytes(self):
        """Test file size formatting (bytes)."""
        size = file_storage.format_file_size(512)
        assert size == "512 B"
