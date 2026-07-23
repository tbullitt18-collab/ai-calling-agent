"""
API routes for Rain Check.
RESTful endpoints for call management and analytics.
"""

from flask import Blueprint, request, jsonify
import logging
from app.services.vonage_service import initiate_outbound_call

logger = logging.getLogger(__name__)
api_bp = Blueprint('api', __name__)


@api_bp.route('/call/initiate', methods=['POST'])
def api_initiate_call():
    """
    Initiate an outbound call via Vonage.
    Expects: {"to": "+1234567890", "reason": "...", "notes": "...", "voice_id": "..."}
    """
    data = request.get_json(silent=True) or {}
    to_number = data.get('to')
    reason = data.get('reason')
    notes = data.get('notes')
    voice_id = data.get('voice_id')
    
    if not to_number:
        return jsonify({"error": "Missing 'to' phone number"}), 400
        
    try:
        result = initiate_outbound_call(to_number, reason=reason, notes=notes, voice_id=voice_id)
        return jsonify({
            "status": "initiated",
            "call_uuid": result.get('uuid'),
            "message": f"Call to {to_number} initiated."
        })
    except Exception as e:
        logger.error(f"API call initiation error: {e}")
        return jsonify({"error": str(e)}), 500


@api_bp.route('/call/<call_uuid>', methods=['GET'])
def api_get_call(call_uuid: str):
    """Get call details by UUID from MongoDB."""
    from app.services.call_logger_service import get_call_logger
    
    try:
        call_logger = get_call_logger()
        call = call_logger.get_call(call_uuid)
        
        if not call:
            return jsonify({"error": "Call not found"}), 404
        
        # Convert ObjectId for JSON serialization
        call['_id'] = str(call['_id'])
        return jsonify(call)
    except Exception as e:
        logger.error(f"Error fetching call {call_uuid}: {e}")
        return jsonify({"error": str(e)}), 404


@api_bp.route('/calls/recent', methods=['GET'])
def api_recent_calls():
    """
    List recent calls from MongoDB.
    Query params: limit (default 10)
    """
    from app.services.call_logger_service import get_call_logger
    
    limit = request.args.get('limit', 10, type=int)
    
    try:
        call_logger = get_call_logger()
        calls = call_logger.get_recent_calls(limit=limit)
        
        # Convert ObjectIds and datetimes for JSON serialization
        for call in calls:
            call['_id'] = str(call['_id'])
            for key, val in list(call.items()):
                if hasattr(val, 'isoformat'):
                    call[key] = val.isoformat()
        
        return jsonify({"calls": calls})
    except Exception as e:
        logger.error(f"Error fetching recent calls: {e}")
        return jsonify({"calls": [], "error": str(e)}), 200


@api_bp.route('/analytics', methods=['GET'])
def api_analytics():
    """Get call analytics summary from MongoDB."""
    from app.services.call_logger_service import get_call_logger
    
    try:
        call_logger = get_call_logger()
        analytics = call_logger.get_analytics()
        
        if analytics:
            analytics['_id'] = str(analytics['_id'])
            return jsonify(analytics)
        else:
            return jsonify({
                "period": "today",
                "total_calls": 0,
                "completed_calls": 0,
                "total_duration_seconds": 0
            })
    except Exception as e:
        logger.error(f"Error fetching analytics: {e}")
        return jsonify({"error": str(e)}), 500
