import sqlite3
from datetime import datetime
from typing import Optional, Dict, List

DB_NAME = "contracts.db"


def init_users_table():
    """Initialize users table in database."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
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
    
    conn.commit()
    conn.close()


def create_default_admin():
    """Create default admin user if no users exist."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    
    if count == 0:
        # Import here to avoid circular dependency
        import bcrypt
        
        # Default admin credentials
        # Username: admin, Password: admin123
        # CHANGE THIS IN PRODUCTION!
        default_password = "admin123"
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(default_password.encode('utf-8'), salt).decode('utf-8')
        
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """, ("admin", "admin@contractiq.com", password_hash, "Admin"))
        
        conn.commit()
        print("✅ Default admin user created (username: admin, password: admin123)")
        print("⚠️  CHANGE THE DEFAULT PASSWORD IMMEDIATELY!")
    
    conn.close()


def get_user_by_username(username: str) -> Optional[Dict]:
    """Get user by username."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, username, email, password_hash, role, created_at, last_login, is_active
    FROM users
    WHERE username = ? AND is_active = 1
    """, (username,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_by_email(email: str) -> Optional[Dict]:
    """Get user by email."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, username, email, password_hash, role, created_at, last_login, is_active
    FROM users
    WHERE email = ? AND is_active = 1
    """, (email,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Get user by ID."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, username, email, password_hash, role, created_at, last_login, is_active
    FROM users
    WHERE id = ? AND is_active = 1
    """, (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def create_user(username: str, email: str, password_hash: str, role: str = "User") -> bool:
    """
    Create a new user.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        INSERT INTO users (username, email, password_hash, role)
        VALUES (?, ?, ?, ?)
        """, (username, email, password_hash, role))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username or email already exists
        return False


def update_last_login(user_id: int):
    """Update user's last login timestamp."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("""
    UPDATE users
    SET last_login = CURRENT_TIMESTAMP
    WHERE id = ?
    """, (user_id,))
    
    conn.commit()
    conn.close()


def get_all_users() -> List[Dict]:
    """Get all users (admin only)."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    cursor.execute("""
    SELECT id, username, email, role, created_at, last_login, is_active
    FROM users
    ORDER BY created_at DESC
    """)
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def update_user_role(user_id: int, role: str) -> bool:
    """Update user role (admin only)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users
        SET role = ?
        WHERE id = ?
        """, (role, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def deactivate_user(user_id: int) -> bool:
    """Deactivate a user (admin only)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users
        SET is_active = 0
        WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def activate_user(user_id: int) -> bool:
    """Activate a user (admin only)."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users
        SET is_active = 1
        WHERE id = ?
        """, (user_id,))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False


def change_password(user_id: int, new_password_hash: str) -> bool:
    """Change user password."""
    try:
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("""
        UPDATE users
        SET password_hash = ?
        WHERE id = ?
        """, (new_password_hash, user_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False