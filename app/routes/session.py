"""
Call scheduling routes for Rain Check.
"""

from flask import Blueprint, request, jsonify
import logging
import re
from app import scheduler

logger = logging.getLogger(__name__)
session_bp = Blueprint('session', __name__)


def _normalize_phone(number: str) -> str:
    """
    Normalize phone number to E.164 format.
    Accepts: 10 digits, +1XXXXXXXXXX, 1XXXXXXXXXX, (XXX) XXX-XXXX, etc.
    Returns: +1XXXXXXXXXX for US numbers.
    """
    if not number:
        return number
    
    # Strip everything that isn't a digit or +
    digits = re.sub(r'[^\d]', '', number)
    
    # 10 digits → US number, prepend +1
    if len(digits) == 10:
        return f"+1{digits}"
    # 11 digits starting with 1 → US number, prepend +
    elif len(digits) == 11 and digits.startswith('1'):
        return f"+{digits}"
    # Already has + prefix
    elif number.startswith('+'):
        return number
    # Fallback: prepend +
    else:
        return f"+{digits}"


@session_bp.route('/schedule', methods=['POST'])
def schedule_call():
    """
    Schedule an automated call.
    Expects: {"to_number": "1234567890", "time": "06:00"}
    Phone numbers are auto-normalized to +1XXXXXXXXXX format.
    """
    data = request.get_json()
    to_number = _normalize_phone(data.get('to_number', ''))
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
        logger.error(f"Scheduling error: {e}", exc_info=True)
        return jsonify({"error": f"Scheduling failed: {e}"}), 500

@session_bp.route('/call-now', methods=['POST'])
def call_now():
    """Initiate a call immediately. Phone numbers auto-normalized."""
    from app.services.vonage_service import initiate_outbound_call
    data = request.get_json()
    to_number = _normalize_phone(data.get('to_number', ''))
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
        logger.error(f"Immediate call error: {e}", exc_info=True)
        return jsonify({"error": f"Call failed: {e}"}), 500


