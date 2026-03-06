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
        "telephony": "Vonage Voice API + WebSocket",
        "environment": FLASK_ENV
    })

@health_bp.route('/health', methods=['GET'])
def health():
    """Detailed health status."""
    return jsonify({"status": "ok"})

@health_bp.route('/health/db', methods=['GET'])
def health_db():
    """Debug: check MongoDB connectivity."""
    import os
    uri = os.getenv('MONGODB_URI', 'NOT SET')
    # Mask the URI for security (show scheme + host only)
    if uri and uri != 'NOT SET':
        masked = uri[:20] + '...' + uri[-20:] if len(uri) > 40 else uri
    else:
        masked = uri

    result = {"mongodb_uri_set": uri != 'NOT SET', "uri_preview": masked}

    try:
        from pymongo import MongoClient
        client = MongoClient(uri, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        result["connection"] = "ok"
        result["databases"] = client.list_database_names()
    except Exception as e:
        result["connection"] = "failed"
        result["error"] = str(e)

    return jsonify(result)
