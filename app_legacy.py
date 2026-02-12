"""
Rain Check - AI Voice Application
Main Flask application with Twilio webhooks and Media Stream handling.
"""

import asyncio
import logging
import json
import base64
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from flask_sock import Sock

from config import BASE_URL, FLASK_ENV
from modules.twilio_api import generate_answer_twiml, initiate_outbound_call
from modules.session_manager import SessionManager
from modules.intent_detector import detect_intent, should_ask_followup
from modules.conversation_engine import ConversationEngine
from modules.elevenlabs_realtime import ElevenLabsRealtimeClient
from modules.call_logger import CallLogger

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
CORS(app)
sock = Sock(app)

# Initialize services
session_manager = SessionManager()
conversation_engine = ConversationEngine()
call_logger = CallLogger()


@app.route('/', methods=['GET'])
def index():
    """Health check endpoint."""
    return jsonify({
        "service": "Rain Check AI Voice Application",
        "version": "2.0.0",
        "status": "operational",
        "telephony": "Twilio + Media Streams"
    })


@app.route('/webhook/answer', methods=['POST'])
def webhook_answer():
    """
    Twilio Answer webhook - called when an incoming call is received.
    Returns TwiML to establish Media Stream WebSocket connection.
    """
    try:
        # Twilio sends form data, not JSON
        call_sid = request.values.get('CallSid')
        caller = request.values.get('From', 'unknown')
        
        logger.info(f"Incoming call: {call_sid} from {caller}")
        
        # Create session for this call
        session_manager.create_session(call_sid, caller)
        
        # Generate TwiML
        twiml = generate_answer_twiml(call_sid)
        return Response(twiml, mimetype='text/xml')
        
    except Exception as e:
        logger.error(f"Error in answer webhook: {e}")
        # Fallback TwiML
        return Response('<Response><Say>System error. Please try again.</Say></Response>', mimetype='text/xml')


@app.route('/webhook/outbound-twiml', methods=['POST'])
def webhook_outbound():
    """
    Twilio Outbound webhook - called when an outbound call connects.
    Returns TwiML to connect Media Stream.
    """
    call_sid = request.values.get('CallSid')
    twiml = generate_answer_twiml(call_sid)
    return Response(twiml, mimetype='text/xml')


@app.route('/api/call/initiate', methods=['POST'])
def api_initiate_call():
    """API endpoint to initiate an outbound call."""
    try:
        data = request.get_json()
        to_number = data.get('to')
        
        if not to_number:
            return jsonify({"error": "Phone number required"}), 400
            
        result = initiate_outbound_call(to_number)
        return jsonify({
            "status": "initiated",
            "call_uuid": result.get('uuid')
        })
        
    except Exception as e:
        logger.error(f"Error initiating call: {e}")
        return jsonify({"error": str(e)}), 500


@sock.route('/ws/audio/<call_sid>')
def media_stream(ws, call_sid: str):
    """
    WebSocket endpoint for Twilio Media Streams.
    Handles bidirectional audio:
    - Receives mu-law audio from Twilio (needs decoding/transcoding if not handled)
    - Sends audio to ElevenLabs (requires correct format)
    """
    logger.info(f"Media Stream connected for: {call_sid}")
    
    async def handle_stream():
        eleven_client = ElevenLabsRealtimeClient()
        # ElevenLabs Conversational AI mode
        await eleven_client.connect_conversational()
        
        stream_sid = None
        logger.info(f"Stream handler started for {call_sid}")
        
        async def receive_from_twilio():
            nonlocal stream_sid
            try:
                while True:
                    # BLOCKING call in a separate thread if needed, 
                    # but flask-sock is sync. Let's use it as a stream.
                    message = ws.receive()
                    if message is None:
                        break
                    
                    data = json.loads(message)
                    if data.get('event') == 'start':
                        stream_sid = data['start']['streamSid']
                        logger.info(f"Twilio stream started: {stream_sid}")
                    elif data.get('event') == 'media':
                        payload = data['media']['payload']
                        # Send base64 mulaw directly to ElevenLabs ConvAI 
                        # (It can handle mulaw if configured or we transcode)
                        # For now, let's assume PCM 16k is needed unless we changed client
                        await eleven_client.send_audio_input(base64.b64decode(payload))
                    elif data.get('event') == 'stop':
                        logger.info("Twilio stream stopped")
                        break
            except Exception as e:
                logger.error(f"Error receiving from Twilio: {e}")

        async def send_to_twilio():
            try:
                async for response in eleven_client.receive_conversational_responses():
                    if response.get('type') == 'audio':
                        audio_payload = response.get('audio')
                        if audio_payload and stream_sid:
                            ws.send(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": { "payload": audio_payload }
                            }))
                    elif response.get('type') == 'agent_response':
                        logger.info(f"AI: {response.get('agent_response')}")
            except Exception as e:
                logger.error(f"Error sending to Twilio: {e}")

        # Run both tasks concurrently
        await asyncio.gather(receive_from_twilio(), send_to_twilio())

    # Use a threading wrapper or different approach if flask-sock blocks
    # For now, let's attempt to run the async loop
    try:
        asyncio.run(handle_stream())
    except Exception as e:
        logger.error(f"Fatal stream error: {e}")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=(FLASK_ENV == 'development'))
