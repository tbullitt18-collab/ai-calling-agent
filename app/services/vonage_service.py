"""
Vonage Voice API integration for Rain Check.
Handles NCCO generation, call routing, and WebSocket audio streaming.
Uses Vonage Python SDK v4 with API key/secret + private key auth.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)

# Lazy initialization
_vonage_voice = None
_app_id_cache = None


def _discover_application_id() -> str:
    """
    Discover the Vonage Application ID using API key/secret.
    Searches for the 'Rain Check' app or returns the first app found.
    """
    global _app_id_cache
    if _app_id_cache:
        return _app_id_cache
    
    from app.config import VONAGE_API_KEY, VONAGE_API_SECRET, VONAGE_APPLICATION_ID
    
    # If explicitly set, use it
    if VONAGE_APPLICATION_ID:
        _app_id_cache = VONAGE_APPLICATION_ID
        return _app_id_cache
    
    # Otherwise discover via REST API
    try:
        resp = requests.get(
            "https://api.nexmo.com/v2/applications",
            auth=(VONAGE_API_KEY, VONAGE_API_SECRET),
            headers={"Accept": "application/json"},
            timeout=10
        )
        if resp.status_code == 200:
            apps = resp.json().get("_embedded", {}).get("applications", [])
            for app in apps:
                if "rain" in app.get("name", "").lower():
                    _app_id_cache = app["id"]
                    logger.info(f"Discovered Vonage app: {app['name']} ({_app_id_cache})")
                    return _app_id_cache
            if apps:
                _app_id_cache = apps[0]["id"]
                logger.info(f"Using first Vonage app: {apps[0].get('name')} ({_app_id_cache})")
                return _app_id_cache
        
        logger.warning(f"Vonage app discovery failed ({resp.status_code}): {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Vonage app discovery error: {e}")
    
    return None


def _get_voice():
    """Get or create Vonage Voice client (SDK v4 pattern)."""
    global _vonage_voice
    if _vonage_voice is None:
        from vonage_http_client import HttpClient, Auth
        from vonage_voice import Voice
        from app.config import VONAGE_API_KEY, VONAGE_API_SECRET, VONAGE_PRIVATE_KEY_PATH
        
        app_id = _discover_application_id()
        
        auth = Auth(
            api_key=VONAGE_API_KEY,
            api_secret=VONAGE_API_SECRET,
            application_id=app_id,
            private_key=VONAGE_PRIVATE_KEY_PATH
        )
        http_client = HttpClient(auth=auth)
        _vonage_voice = Voice(http_client)
        logger.info(f"Vonage Voice client initialized (App: {app_id})")
    return _vonage_voice


def send_sms(to_number: str, text: str) -> str:
    """
    Dispatches an SMS via Vonage REST API.
    to_number should be E.164 format: e.g. "14045551234"
    """
    import os
    import requests
    from app.config import VONAGE_API_KEY, VONAGE_API_SECRET, VONAGE_NUMBER
    
    api_key = VONAGE_API_KEY
    api_secret = VONAGE_API_SECRET
    from_number = VONAGE_NUMBER  # Your provisioned Vonage number

    if not all([api_key, api_secret, from_number]):
        return "SMS failed: Missing Vonage credentials in environment."

    # Sanitize number — strip non-digits, ensure no leading +
    clean_to = "".join(filter(str.isdigit, to_number))

    payload = {
        "api_key": api_key,
        "api_secret": api_secret,
        "to": clean_to,
        "from": from_number,
        "text": text
    }

    try:
        resp = requests.post(
            "https://rest.nexmo.com/sms/json",
            data=payload,
            timeout=5
        )
        resp.raise_for_status()
        data = resp.json()
        status = data["messages"][0]["status"]
        if status == "0":
            return f"SMS sent successfully to {to_number}."
        else:
            error = data["messages"][0].get("error-text", "Unknown error")
            return f"SMS failed with Vonage status {status}: {error}"
    except Exception as e:
        return f"SMS dispatch error: {str(e)}"


def generate_answer_ncco(call_uuid: str, reason: str = None, voice_id: str = None) -> list:
    """
    Generate NCCO for answering a call with WebSocket audio stream.
    
    Flow:
      1. Greeting via 'talk' action
      2. Connect to WebSocket for bidirectional audio
    """
    from app.config import BASE_URL
    
    ws_host = BASE_URL.replace("https://", "").replace("http://", "")
    ws_uri = f"wss://{ws_host}/ws/audio/{call_uuid}"
    
    headers = {}
    if reason:
        headers["X-Reason"] = reason
    if voice_id:
        headers["X-Voice-Id"] = voice_id
    
    logger.info(f"Generated NCCO WebSocket URI: {ws_uri}")
    
    ncco = [
        {
            "action": "connect",
            "endpoint": [
                {
                    "type": "websocket",
                    "uri": ws_uri,
                    "content-type": "audio/l16;rate=16000",
                    "headers": headers
                }
            ]
        }
    ]
    
    return ncco


def generate_error_ncco(message: str = "An error occurred. Please try again later.") -> list:
    """Generate error NCCO response."""
    return [{"action": "talk", "text": message}]


def initiate_outbound_call(
    to_number: str,
    reason: str = None,
    notes: str = None,
    voice_id: str = None
) -> dict:
    """
    Initiate an outbound call via Vonage Voice API.
    """
    from app.config import VONAGE_NUMBER, BASE_URL
    from urllib.parse import urlencode

    voice = _get_voice()
    
    params = {}
    if reason:
        params["reason"] = reason
    if notes:
        params["notes"] = notes
    if voice_id:
        params["voice_id"] = voice_id
    
    query = f"?{urlencode(params)}" if params else ""
    answer_url = f"{BASE_URL}/webhook/answer{query}"
    event_url = f"{BASE_URL}/webhook/events"
    
    logger.info(f"Initiating outbound call to {to_number} via Vonage")
    
    to_clean = to_number.lstrip("+")
    from_clean = VONAGE_NUMBER.lstrip("+")
    
    try:
        # Use REST API directly for maximum compatibility
        from app.config import VONAGE_API_KEY, VONAGE_API_SECRET
        import jwt, time, uuid
        
        app_id = _discover_application_id()
        if not app_id:
            raise ValueError("Vonage Application ID not available")
        
        # Generate JWT for Voice API
        from app.config import VONAGE_PRIVATE_KEY_PATH
        with open(VONAGE_PRIVATE_KEY_PATH, 'r') as f:
            private_key = f.read()
        
        payload = {
            "application_id": app_id,
            "iat": int(time.time()),
            "jti": str(uuid.uuid4()),
            "exp": int(time.time()) + 3600
        }
        token = jwt.encode(payload, private_key, algorithm="RS256")
        
        resp = requests.post(
            "https://api.nexmo.com/v1/calls",
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            },
            json={
                "to": [{"type": "phone", "number": to_clean}],
                "from": {"type": "phone", "number": from_clean},
                "answer_url": [answer_url],
                "event_url": [event_url]
            },
            timeout=15
        )
        
        if resp.status_code in (200, 201):
            data = resp.json()
            call_uuid = data.get("uuid", data.get("conversation_uuid"))
            logger.info(f"Vonage call initiated: {call_uuid}")
            return {"uuid": call_uuid}
        else:
            error_detail = resp.text[:500]
            logger.error(f"Vonage call error: {resp.status_code} {error_detail}")
            raise Exception(f"Vonage API error ({resp.status_code}): {error_detail}")
            
    except Exception as e:
        logger.error(f"Vonage call error: {e}")
        raise
