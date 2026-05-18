import os
import shutil
from pathlib import Path
from typing import Optional

# Add this line — makes the base dir patchable in tests
STORAGE_BASE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "uploads")

# Storage configuration
UPLOAD_DIR = "user_uploads"
MAX_FILE_SIZE_MB = 50  # Maximum file size per document
MAX_TOTAL_STORAGE_MB = 500  # Maximum total storage per user

def init_storage():
    """Initialize storage directory structure."""
    Path(UPLOAD_DIR).mkdir(exist_ok=True)


def get_user_storage_path(user_id: int) -> Path:
    """Get the storage directory path for a user."""
    user_dir = Path(UPLOAD_DIR) / f"user_{user_id}"
    user_dir.mkdir(exist_ok=True)
    return user_dir


def save_uploaded_file(user_id: int, file_hash: str, file_name: str, file_bytes: bytes) -> Optional[str]:
    """
    Save an uploaded file to user's storage directory.

    Args:
        user_id: User ID
        file_hash: SHA256 hash of the file
        file_name: Original filename
        file_bytes: File content as bytes

    Returns:
        Relative file path if successful, None otherwise
    """
    try:
        # Get file extension
        ext = Path(file_name).suffix or ".pdf"

        # Create filename with hash to avoid collisions
        safe_filename = f"{file_hash}{ext}"

        # Get user storage path
        user_dir = get_user_storage_path(user_id)
        file_path = user_dir / safe_filename

        # Write file
        with open(file_path, "wb") as f:
            f.write(file_bytes)

        # Return relative path
        return str(file_path.relative_to(Path.cwd()))

    except Exception as e:
        print(f"Error saving file: {e}")
        return None


def get_file_size(file_path: str) -> int:
    """Get file size in bytes."""
    try:
        return os.path.getsize(file_path)
    except Exception:
        return 0


def delete_file(file_path: str) -> bool:
    """
    Delete a file from storage.

    Args:
        file_path: Path to the file

    Returns:
        True if successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            return True
        return False
    except Exception as e:
        print(f"Error deleting file: {e}")
        return False


def get_user_storage_usage(user_id: int) -> dict:
    """
    Get storage usage statistics for a user.

    Returns:
        Dict with total_bytes, total_mb, file_count
    """
    user_dir = get_user_storage_path(user_id)

    total_bytes = 0
    file_count = 0

    try:
        for file in user_dir.glob("**/*"):
            if file.is_file():
                total_bytes += file.stat().st_size
                file_count += 1
    except Exception:
        pass

    return {
        "total_bytes": total_bytes,
        "total_mb": round(total_bytes / (1024 * 1024), 2),
        "file_count": file_count,
        "max_mb": MAX_TOTAL_STORAGE_MB,
        "usage_percent": round((total_bytes / (MAX_TOTAL_STORAGE_MB * 1024 * 1024)) * 100, 1)
    }


def check_storage_quota(user_id: int, new_file_size: int) -> tuple[bool, str]:
    """
    Check if user has enough storage quota for a new file.

    Args:
        user_id: User ID
        new_file_size: Size of new file in bytes

    Returns:
        Tuple of (can_upload: bool, message: str)
    """
    usage = get_user_storage_usage(user_id)

    # Check file size limit
    file_size_mb = new_file_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        return False, f"File exceeds maximum size of {MAX_FILE_SIZE_MB}MB"

    # Check total storage limit
    new_total_mb = usage["total_mb"] + file_size_mb
    if new_total_mb > MAX_TOTAL_STORAGE_MB:
        remaining_mb = MAX_TOTAL_STORAGE_MB - usage["total_mb"]
        return False, f"Storage quota exceeded. You have {remaining_mb:.1f}MB remaining."

    return True, "OK"


def format_file_size(size_bytes: int) -> str:
    """Format file size in human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
