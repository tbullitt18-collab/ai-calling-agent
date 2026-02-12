"""
Call scheduling routes for Rain Check.
"""

from flask import Blueprint, request, jsonify
import logging
from app import scheduler

logger = logging.getLogger(__name__)
session_bp = Blueprint('session', __name__)

@session_bp.route('/schedule', methods=['POST'])
def schedule_call():
    """
    Schedule an automated call.
    Expects: {"to_number": "+1234567890", "time": "06:00"}
    """
    data = request.get_json()
    to_number = data.get('to_number')
    time_str = data.get('time')
    reason = data.get('reason')
    notes = data.get('notes')
    voice_id = data.get('voice_id')
    
    if not to_number or not time_str:
        return jsonify({"error": "Missing to_number or time"}), 400
        
    try:
        job_id = scheduler.schedule_call(to_number, time_str, reason=reason, notes=notes, voice_id=voice_id)
        return jsonify({
            "status": "scheduled",
            "job_id": job_id,
            "message": f"Call scheduled for {time_str} ({reason})"
        })


    except Exception as e:
        logger.error(f"Scheduling error: {e}")
        return jsonify({"error": str(e)}), 500

@session_bp.route('/call-now', methods=['POST'])
def call_now():
    """Initiate a call immediately."""
    from app.services.vonage_service import initiate_outbound_call
    data = request.get_json()
    to_number = data.get('to_number')
    reason = data.get('reason')
    notes = data.get('notes')
    voice_id = data.get('voice_id')
    
    if not to_number:
        return jsonify({"error": "Missing to_number"}), 400
        
    try:
        result = initiate_outbound_call(to_number, reason=reason, notes=notes, voice_id=voice_id)
        return jsonify({
            "status": "initiated",
            "call_sid": result.get('uuid'),
            "message": f"Call to {to_number} initiated immediately."
        })
    except Exception as e:
        logger.error(f"Immediate call error: {e}")
        return jsonify({"error": str(e)}), 500

