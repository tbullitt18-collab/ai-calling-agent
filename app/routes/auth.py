"""
Authentication routes for Rain Check.
MongoDB-backed user registration + session-based login.
"""

from flask import Blueprint, request, jsonify, session, redirect
import hashlib
import os
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


def _get_users_collection():
    """Get the users collection from MongoDB."""
    from pymongo import MongoClient
    uri = os.getenv('MONGODB_URI', 'mongodb://localhost:27017')
    client = MongoClient(uri, serverSelectionTimeoutMS=3000)
    return client['raincheck']['users']


def _hash_password(password: str) -> str:
    """Hash password with SHA-256 + salt."""
    salt = os.getenv('FLASK_SECRET_KEY', 'raincheck-dev-secret-2025')
    return hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Serve the login page."""
    from flask import current_app
    return current_app.send_static_file('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle login form submission."""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    # 1. Check env-var admin credentials (always works as fallback)
    admin_user = os.getenv('RAINCHECK_USERNAME', 'admin')
    admin_pass = os.getenv('RAINCHECK_PASSWORD', 'raincheck2025')

    if username == admin_user and password == admin_pass:
        session['authenticated'] = True
        session['username'] = username
        logger.info(f"Admin '{username}' logged in")
        return jsonify({"status": "ok", "redirect": "/dashboard"})

    # 2. Check MongoDB users
    try:
        users = _get_users_collection()
        user = users.find_one({"username": username})
        if user and user.get('password_hash') == _hash_password(password):
            session['authenticated'] = True
            session['username'] = username
            logger.info(f"User '{username}' logged in")
            return jsonify({"status": "ok", "redirect": "/dashboard"})
    except Exception as e:
        logger.error(f"MongoDB auth check failed: {e}")

    logger.warning(f"Failed login attempt for '{username}'")
    return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route('/register', methods=['POST'])
def register():
    """Create a new user account."""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    confirm = data.get('confirm_password', '').strip()

    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400

    if len(username) < 3:
        return jsonify({"error": "Username must be at least 3 characters"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    if password != confirm:
        return jsonify({"error": "Passwords don't match"}), 400

    try:
        users = _get_users_collection()

        # Check if username already exists
        if users.find_one({"username": username}):
            return jsonify({"error": "Username already taken"}), 409

        # Create user
        users.insert_one({
            "username": username,
            "password_hash": _hash_password(password),
        })

        # Auto-login after registration
        session['authenticated'] = True
        session['username'] = username
        logger.info(f"New user registered: '{username}'")
        return jsonify({"status": "ok", "redirect": "/dashboard"})

    except Exception as e:
        logger.error(f"Registration failed: {e}")
        return jsonify({"error": "Registration failed. Please try again."}), 500


@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    """Handle forgot password requests."""
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    # In a real app, we would:
    # 1. Lookup user by username
    # 2. Generate a secure reset token
    # 3. Send email to the user's associated email address
    
    logger.info(f"Password reset requested for '{username}'")
    
    # Always return success to prevent username enumeration
    return jsonify({"status": "ok", "message": "If an account exists, a reset link has been sent."})


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return jsonify({"status": "ok", "redirect": "/login"})
