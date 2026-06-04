"""
User profile routes for Rain Check.
Handles permanent display name, setup/config, and profile retrieval.
"""

from flask import Blueprint, request, jsonify, session
import logging
from app.models.user_profile import UserProfile

logger = logging.getLogger(__name__)
profile_bp = Blueprint('profile', __name__)
user_profile_model = UserProfile()


@profile_bp.route('/', methods=['GET'])
def get_profile():
    """Get the current user's profile."""
    username = session.get('username')
    if not username:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        profile = user_profile_model.get_profile(username)
        if profile:
            return jsonify(profile)
        else:
            return jsonify({
                "username": username,
                "display_name": None,
                "setup": {},
                "needs_setup": True
            })
    except Exception as e:
        logger.error(f"Error fetching profile: {e}")
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/display-name', methods=['POST'])
def set_display_name():
    """
    Set a permanent display name.
    Once set, this CANNOT be changed.
    """
    username = session.get('username')
    if not username:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}
    display_name = data.get('display_name', '').strip()

    if not display_name:
        return jsonify({"error": "Display name is required"}), 400

    if len(display_name) < 2 or len(display_name) > 50:
        return jsonify({"error": "Display name must be 2-50 characters"}), 400

    try:
        profile = user_profile_model.set_display_name(username, display_name)
        return jsonify({
            "status": "success",
            "message": "Display name set permanently.",
            "profile": profile
        })
    except ValueError as e:
        return jsonify({"error": str(e)}), 409
    except Exception as e:
        logger.error(f"Error setting display name: {e}")
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/setup', methods=['POST'])
def update_setup():
    """
    Update workplace setup info (schedule, employee ID, etc.).
    This can be updated at any time.
    """
    username = session.get('username')
    if not username:
        return jsonify({"error": "Not authenticated"}), 401

    data = request.get_json(silent=True) or {}

    if not data:
        return jsonify({"error": "No setup data provided"}), 400

    try:
        profile = user_profile_model.update_setup(username, data)
        return jsonify({
            "status": "success",
            "message": "Setup updated successfully.",
            "profile": profile
        })
    except Exception as e:
        logger.error(f"Error updating setup: {e}")
        return jsonify({"error": str(e)}), 500


@profile_bp.route('/setup', methods=['GET'])
def get_setup():
    """Get the current user's setup info."""
    username = session.get('username')
    if not username:
        return jsonify({"error": "Not authenticated"}), 401

    try:
        profile = user_profile_model.get_profile(username)
        if profile:
            return jsonify({
                "setup": profile.get('setup', {}),
                "is_complete": user_profile_model.is_setup_complete(username)
            })
        return jsonify({"setup": {}, "is_complete": False})
    except Exception as e:
        logger.error(f"Error fetching setup: {e}")
        return jsonify({"error": str(e)}), 500
