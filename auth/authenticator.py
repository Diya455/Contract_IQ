import streamlit as st
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict
from database.users_db import (
    get_user_by_username,
    get_user_by_email,
    create_user,
    update_last_login
)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed_password: str) -> bool:
    """Verify a password against a hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8'))


def login_user(username: str, password: str) -> Optional[Dict]:
    """
    Authenticate a user.
    
    Returns:
        User dict if successful, None otherwise
    """
    user = get_user_by_username(username)
    
    if user and verify_password(password, user['password_hash']):
        update_last_login(user['id'])
        return user
    
    return None


def register_user(username: str, email: str, password: str, role: str = "User") -> bool:
    """
    Register a new user.
    
    Returns:
        True if successful, False if user exists
    """
    # Check if username or email already exists
    if get_user_by_username(username):
        return False
    
    if get_user_by_email(email):
        return False
    
    # Hash password and create user
    password_hash = hash_password(password)
    return create_user(username, email, password_hash, role)


def init_session_state():
    """Initialize authentication session state."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    
    if 'user' not in st.session_state:
        st.session_state.user = None
    
    if 'username' not in st.session_state:
        st.session_state.username = None
    
    if 'role' not in st.session_state:
        st.session_state.role = None
    
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None


def logout():
    """Log out the current user."""
    st.session_state.authenticated = False
    st.session_state.user = None
    st.session_state.username = None
    st.session_state.role = None
    st.session_state.user_id = None


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return st.session_state.get('authenticated', False)


def is_admin() -> bool:
    """Check if current user is an admin."""
    return st.session_state.get('role') == 'Admin'


def get_current_user() -> Optional[Dict]:
    """Get current authenticated user."""
    return st.session_state.get('user')


def require_auth(func):
    """Decorator to require authentication for a function."""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("⚠️ Please log in to access this feature.")
            return None
        return func(*args, **kwargs)
    return wrapper


def require_admin(func):
    """Decorator to require admin role for a function."""
    def wrapper(*args, **kwargs):
        if not is_authenticated():
            st.warning("⚠️ Please log in to access this feature.")
            return None
        
        if not is_admin():
            st.error("🚫 Admin access required.")
            return None
        
        return func(*args, **kwargs)
    return wrapper


def show_login_form():
    """Display login form."""
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h2 style='color: #f0f2f6; font-weight: 700;'>🔐 Login to ContractIQ</h2>
        <p style='color: #7b8299; font-size: 0.9rem;'>Enter your credentials to continue</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("login_form"):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("🔓 Login", use_container_width=True)
        
        if submit:
            if not username or not password:
                st.error("❌ Please enter both username and password")
                return False
            
            user = login_user(username, password)
            
            if user:
                st.session_state.authenticated = True
                st.session_state.user = user
                st.session_state.username = user['username']
                st.session_state.role = user['role']
                st.session_state.user_id = user['id']
                st.success(f"✅ Welcome back, {username}!")
                st.rerun()
                return True
            else:
                st.error("❌ Invalid username or password")
                return False
    
    return False


def show_registration_form():
    """Display registration form."""
    st.markdown("""
    <div style='text-align: center; padding: 20px 0;'>
        <h2 style='color: #f0f2f6; font-weight: 700;'>📝 Register New Account</h2>
        <p style='color: #7b8299; font-size: 0.9rem;'>Create your ContractIQ account</p>
    </div>
    """, unsafe_allow_html=True)
    
    with st.form("registration_form"):
        username = st.text_input("Username", key="reg_username")
        email = st.text_input("Email", key="reg_email")
        password = st.text_input("Password", type="password", key="reg_password")
        password_confirm = st.text_input("Confirm Password", type="password", key="reg_password_confirm")
        
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            submit = st.form_submit_button("✨ Create Account", use_container_width=True)
        
        if submit:
            # Validation
            if not username or not email or not password:
                st.error("❌ All fields are required")
                return False
            
            if len(username) < 3:
                st.error("❌ Username must be at least 3 characters")
                return False
            
            if "@" not in email or "." not in email:
                st.error("❌ Invalid email address")
                return False
            
            if len(password) < 6:
                st.error("❌ Password must be at least 6 characters")
                return False
            
            if password != password_confirm:
                st.error("❌ Passwords do not match")
                return False
            
            # Register user
            if register_user(username, email, password):
                st.success("✅ Account created successfully! You can now log in.")
                return True
            else:
                st.error("❌ Username or email already exists")
                return False
    
    return False


def show_auth_page():
    """Display authentication page with login and registration tabs."""
    st.markdown("""
    <style>
    .auth-container {
        max-width: 500px;
        margin: 50px auto;
        padding: 30px;
        background: #1e212c;
        border: 1px solid #2d3140;
        border-radius: 12px;
    }
    </style>
    """, unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        show_login_form()
    
    with tab2:
        show_registration_form()