"""
MCP routes for Rain Check.
Knowledge Base API endpoints for FAQs, calendar events, and contacts.
"""

from flask import Blueprint, request, jsonify, session
import logging

logger = logging.getLogger(__name__)
mcp_bp = Blueprint('mcp', __name__)


@mcp_bp.route('/seed', methods=['POST'])
def seed_demo_data():
    """Seed demo data for the current user."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')

    try:
        mcp = get_mcp_service()
        result = mcp.seed_demo_data(user_id)
        return jsonify({"status": "seeded", "counts": result})
    except Exception as e:
        logger.error(f"Error seeding demo data: {e}")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/clear', methods=['DELETE'])
def clear_knowledge_base():
    """Clear all knowledge base data for the current user."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')

    try:
        mcp = get_mcp_service()
        result = mcp.clear_knowledge_base(user_id)
        return jsonify({"status": "cleared", "counts": result})
    except Exception as e:
        logger.error(f"Error clearing knowledge base: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------
# FAQ endpoints
# ------------------------------------------------------------------

@mcp_bp.route('/faqs', methods=['GET'])
def get_faqs():
    """Return all FAQs for the current user."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')

    try:
        mcp = get_mcp_service()
        faqs = mcp.get_faqs(user_id)
        return jsonify({"faqs": faqs})
    except Exception as e:
        logger.error(f"Error fetching FAQs: {e}")
        return jsonify({"faqs": [], "error": str(e)}), 200


@mcp_bp.route('/faqs', methods=['POST'])
def add_faq():
    """Add a new FAQ. Expects JSON with 'question' and 'answer'."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')
    data = request.get_json()

    if not data or not data.get('question') or not data.get('answer'):
        return jsonify({"error": "Missing 'question' or 'answer'"}), 400

    try:
        mcp = get_mcp_service()
        inserted_id = mcp.add_faq(user_id, data['question'], data['answer'])
        return jsonify({"status": "created", "id": inserted_id}), 201
    except Exception as e:
        logger.error(f"Error adding FAQ: {e}")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/faqs/<faq_id>', methods=['DELETE'])
def delete_faq(faq_id):
    """Delete an FAQ by ID."""
    from app.services.mongodb_mcp_service import get_mcp_service
    user_id = session.get('username', 'default')
    
    try:
        mcp = get_mcp_service()
        success = mcp.delete_faq(user_id, faq_id)
        if success:
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Not found or not authorized"}), 404
    except Exception as e:
        logger.error(f"Error deleting FAQ: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------
# Calendar endpoints
# ------------------------------------------------------------------

@mcp_bp.route('/calendar', methods=['GET'])
def get_calendar():
    """Return all calendar events for the current user."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')

    try:
        mcp = get_mcp_service()
        events = mcp.get_calendar(user_id)
        return jsonify({"events": events})
    except Exception as e:
        logger.error(f"Error fetching calendar: {e}")
        return jsonify({"events": [], "error": str(e)}), 200


@mcp_bp.route('/calendar', methods=['POST'])
def add_calendar_event():
    """Add a calendar event. Expects JSON with 'title', 'date', optional 'description'."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')
    data = request.get_json()

    if not data or not data.get('title') or not data.get('date'):
        return jsonify({"error": "Missing 'title' or 'date'"}), 400

    try:
        mcp = get_mcp_service()
        inserted_id = mcp.add_calendar_event(
            user_id,
            data['title'],
            data['date'],
            data.get('description', ''),
        )
        return jsonify({"status": "created", "id": inserted_id}), 201
    except Exception as e:
        logger.error(f"Error adding calendar event: {e}")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/calendar/<event_id>', methods=['DELETE'])
def delete_calendar_event(event_id):
    """Delete a calendar event by ID."""
    from app.services.mongodb_mcp_service import get_mcp_service
    user_id = session.get('username', 'default')
    
    try:
        mcp = get_mcp_service()
        success = mcp.delete_calendar_event(user_id, event_id)
        if success:
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Not found or not authorized"}), 404
    except Exception as e:
        logger.error(f"Error deleting calendar event: {e}")
        return jsonify({"error": str(e)}), 500


# ------------------------------------------------------------------
# Contact endpoints
# ------------------------------------------------------------------

@mcp_bp.route('/contacts', methods=['GET'])
def get_contacts():
    """Return all contacts for the current user."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')

    try:
        mcp = get_mcp_service()
        contacts = mcp.get_contacts(user_id)
        return jsonify({"contacts": contacts})
    except Exception as e:
        logger.error(f"Error fetching contacts: {e}")
        return jsonify({"contacts": [], "error": str(e)}), 200


@mcp_bp.route('/contacts', methods=['POST'])
def add_contact():
    """Add a contact. Expects JSON with 'name', 'role', optional 'phone', 'email'."""
    from app.services.mongodb_mcp_service import get_mcp_service

    user_id = session.get('username', 'default')
    data = request.get_json()

    if not data or not data.get('name') or not data.get('role'):
        return jsonify({"error": "Missing 'name' or 'role'"}), 400

    try:
        mcp = get_mcp_service()
        inserted_id = mcp.add_contact(
            user_id,
            data['name'],
            data['role'],
            data.get('phone', ''),
            data.get('email', ''),
        )
        return jsonify({"status": "created", "id": inserted_id}), 201
    except Exception as e:
        logger.error(f"Error adding contact: {e}")
        return jsonify({"error": str(e)}), 500


@mcp_bp.route('/contacts/<contact_id>', methods=['DELETE'])
def delete_contact(contact_id):
    """Delete a contact by ID."""
    from app.services.mongodb_mcp_service import get_mcp_service
    user_id = session.get('username', 'default')
    
    try:
        mcp = get_mcp_service()
        success = mcp.delete_contact(user_id, contact_id)
        if success:
            return jsonify({"status": "deleted"})
        return jsonify({"error": "Not found or not authorized"}), 404
    except Exception as e:
        logger.error(f"Error deleting contact: {e}")
        return jsonify({"error": str(e)}), 500
