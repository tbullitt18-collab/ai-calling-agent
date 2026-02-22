"""
Authentication routes for Rain Check.
Simple session-based login with env-var credentials.
"""

from flask import Blueprint, request, jsonify, session, redirect
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET'])
def login_page():
    """Serve the login page."""
    from flask import current_app
    return current_app.send_static_file('login.html')


@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle login form submission."""
    import os
    
    data = request.get_json(silent=True) or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    
    # Credentials from env vars (defaults for dev)
    valid_user = os.getenv('RAINCHECK_USERNAME', 'admin')
    valid_pass = os.getenv('RAINCHECK_PASSWORD', 'raincheck2025')
    
    if username == valid_user and password == valid_pass:
        session['authenticated'] = True
        session['username'] = username
        logger.info(f"User '{username}' logged in")
        return jsonify({"status": "ok", "redirect": "/"})
    else:
        logger.warning(f"Failed login attempt for '{username}'")
        return jsonify({"error": "Invalid credentials"}), 401


@auth_bp.route('/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    username = session.get('username', 'unknown')
    session.clear()
    logger.info(f"User '{username}' logged out")
    return jsonify({"status": "ok", "redirect": "/login"})
