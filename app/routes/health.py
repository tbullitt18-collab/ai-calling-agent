"""
Health and status routes for Rain Check.
"""

from flask import Blueprint, jsonify
from app.config import FLASK_ENV

health_bp = Blueprint('health', __name__)

@health_bp.route('/', methods=['GET'])
def index():
    """Health check endpoint."""
    return jsonify({
        "service": "Rain Check AI Voice Application",
        "version": "2.0.0",
        "status": "operational",
        "telephony": "Twilio + Media Streams",
        "environment": FLASK_ENV
    })

@health_bp.route('/health', methods=['GET'])
def health():
    """Detailed health status."""
    return jsonify({"status": "ok"})
