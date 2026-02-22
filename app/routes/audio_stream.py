"""
Vonage Audio Streaming and Webhook routes for Rain Check.
Bridges Vonage WebSocket ↔ Claude (conversation) ↔ ElevenLabs (TTS).
"""

import json
import struct
import logging
import asyncio
import io
from flask import Blueprint, request, jsonify
from app import sock
from app.services.vonage_service import generate_answer_ncco, generate_error_ncco
from app.models.call_session import SessionManager
from app.services.conversation_service import ConversationEngine, AgentPersona

logger = logging.getLogger(__name__)
audio_bp = Blueprint('audio', __name__)

session_manager = SessionManager()


# ── Vonage Webhooks ──────────────────────────────────────────────────

@audio_bp.route('/webhook/answer', methods=['GET', 'POST'])
def webhook_answer():
    """
    Vonage Answer webhook — returns NCCO to control the call.
    Supports both GET (standard) and POST (outbound callback).
    """
    try:
        # Vonage sends params as query string (GET) or form data (POST)
        call_uuid = request.values.get('uuid') or request.values.get('conversation_uuid', 'unknown')
        caller = request.values.get('from', 'unknown')
        reason = request.values.get('reason')
        notes = request.values.get('notes')
        voice_id = request.values.get('voice_id')
        
        logger.info(f"Answer webhook: {call_uuid} from {caller}")
        
        # Create session and store context
        session_manager.create_session(call_uuid, caller)
        if reason or notes or voice_id:
            context = {"reason": reason, "notes": notes, "voice_id": voice_id}
            session_manager.set_context(call_uuid, context)
        
        ncco = generate_answer_ncco(call_uuid, reason=reason, voice_id=voice_id)
        return jsonify(ncco)
        
    except Exception as e:
        logger.error(f"Error in answer webhook: {e}")
        return jsonify(generate_error_ncco())


@audio_bp.route('/webhook/events', methods=['POST'])
def webhook_events():
    """Handle Vonage call status events and persist to MongoDB."""
    data = request.get_json(silent=True) or {}
    status = data.get('status', 'unknown')
    uuid = data.get('uuid', 'unknown')
    direction = data.get('direction', 'unknown')
    duration = data.get('duration')
    
    logger.info(f"Call event: {uuid} → {status} (direction={direction})")
    
    # Log terminal call events to MongoDB
    if status in ('completed', 'failed', 'rejected', 'timeout', 'cancelled'):
        logger.info(f"Call {uuid} ended with status: {status}")
        try:
            from app.services.call_logger_service import get_call_logger
            call_logger = get_call_logger()
            if call_logger.calls is not None:
                call_logger.calls.update_one(
                    {"call_uuid": uuid},
                    {"$set": {
                        "status": status,
                        "end_reason": data.get('reason', ''),
                        "duration_seconds": int(duration) if duration else 0,
                    }},
                    upsert=True
                )
                logger.info(f"Call event logged to MongoDB: {uuid} → {status}")
        except Exception as e:
            logger.warning(f"Failed to log call event to MongoDB: {e}")
    
    return '', 204


# ── Audio Processing Helpers ─────────────────────────────────────────

def pcm16_to_float(pcm_bytes: bytes) -> list:
    """Convert PCM 16-bit signed LE audio to float samples."""
    samples = struct.unpack(f'<{len(pcm_bytes)//2}h', pcm_bytes)
    return [s / 32768.0 for s in samples]


def detect_silence(pcm_bytes: bytes, threshold: float = 0.01, min_silent_frames: int = 8000) -> bool:
    """
    Detect if a PCM audio buffer is 'silent' (below energy threshold).
    min_silent_frames = 8000 at 16kHz ≈ 500ms of silence.
    """
    if len(pcm_bytes) < min_silent_frames * 2:
        return False
    
    # Check the tail end for silence
    tail = pcm_bytes[-(min_silent_frames * 2):]
    samples = pcm16_to_float(tail)
    rms = (sum(s * s for s in samples) / len(samples)) ** 0.5
    return rms < threshold


def float_to_pcm16(samples: list) -> bytes:
    """Convert float samples back to PCM 16-bit."""
    clamped = [max(-1.0, min(1.0, s)) for s in samples]
    return struct.pack(f'<{len(clamped)}h', *[int(s * 32767) for s in clamped])


# ── WebSocket Audio Bridge ───────────────────────────────────────────

@sock.route('/ws/audio/<call_uuid>')
def media_stream(ws, call_uuid: str):
    """
    WebSocket handler for Vonage audio streaming.
    
    Flow:
      1. Receive PCM 16kHz audio from Vonage
      2. Buffer until silence detected (end of speech)
      3. Send transcript to Claude for response
      4. Send Claude's response to ElevenLabs TTS
      5. Stream TTS audio back to Vonage
    """
    logger.info(f"WebSocket connected: {call_uuid}")
    
    # Load call context
    context = session_manager.get_context(call_uuid) or {}
    reason = context.get('reason', 'calling in')
    notes = context.get('notes', '')
    voice_id = context.get('voice_id')
    
    # Build persona with call context
    persona = AgentPersona(
        custom_instructions=f"You are calling to report: {reason}. Additional context: {notes}. Be brief and professional."
    )
    engine = ConversationEngine(persona=persona)
    conversation_history = []
    
    # Audio buffer for incoming speech
    audio_buffer = bytearray()
    is_speaking = False
    silence_counter = 0
    
    # Track if we've sent the initial greeting through TTS
    has_greeted = False
    
    logger.info(f"Call context — Reason: {reason}, Voice: {voice_id}")
    
    try:
        # Send initial AI greeting via TTS
        greeting = "Hi, this is calling about a schedule update. I won't be able to make it in today."
        if reason and reason != 'calling in':
            greeting = f"Hi, this is calling about {reason}. I wanted to let you know as soon as possible."
        
        _send_tts_response(ws, greeting, voice_id, engine, conversation_history, call_uuid)
        has_greeted = True
        
        # Main audio receive loop
        while True:
            message = ws.receive()
            if message is None:
                logger.info("WebSocket closed by client")
                break
            
            # Vonage sends binary PCM audio or text control messages
            if isinstance(message, bytes):
                audio_buffer.extend(message)
                
                # Check for end of speech (silence detection)
                if len(audio_buffer) > 16000 * 2:  # At least 1 second of audio
                    if detect_silence(bytes(audio_buffer)):
                        if len(audio_buffer) > 4800:  # Minimum 150ms of actual speech
                            logger.info(f"Speech detected: {len(audio_buffer)} bytes")
                            
                            # Transcribe audio using Deepgram STT
                            manager_text = _transcribe_audio(audio_buffer)
                            
                            if manager_text:
                                logger.info(f"Manager (inferred): {manager_text}")
                                _send_tts_response(
                                    ws, None, voice_id, engine, 
                                    conversation_history, call_uuid,
                                    user_message=manager_text
                                )
                        
                        audio_buffer.clear()
            
            elif isinstance(message, str):
                # Vonage text control messages
                try:
                    data = json.loads(message)
                    event = data.get('event')
                    if event == 'websocket:connected':
                        logger.info("Vonage WebSocket handshake complete")
                    elif event == 'websocket:disconnected':
                        logger.info("Vonage WebSocket disconnected")
                        break
                except json.JSONDecodeError:
                    logger.warning(f"Unknown text message: {message[:100]}")
                    
    except Exception as e:
        logger.error(f"WebSocket error: {e}", exc_info=True)
    finally:
        logger.info(f"WebSocket closed: {call_uuid}")


def _transcribe_audio(audio_buffer: bytearray) -> str:
    """
    Transcribe audio using Deepgram Speech-to-Text API.
    
    Sends PCM 16kHz 16-bit audio to Deepgram's pre-recorded endpoint
    and returns the transcription text.
    
    Args:
        audio_buffer: Raw PCM 16kHz 16-bit LE audio bytes
        
    Returns:
        Transcribed text, or None if transcription failed/empty
    """
    from app.config import DEEPGRAM_API_KEY
    
    duration_seconds = len(audio_buffer) / (16000 * 2)  # 16kHz, 16-bit
    
    if duration_seconds < 0.5:
        return None
    
    if not DEEPGRAM_API_KEY:
        logger.warning("DEEPGRAM_API_KEY not set — cannot transcribe audio")
        return None
    
    try:
        import requests as req
        
        # Send raw PCM audio to Deepgram's pre-recorded endpoint
        response = req.post(
            "https://api.deepgram.com/v1/listen",
            headers={
                "Authorization": f"Token {DEEPGRAM_API_KEY}",
                "Content-Type": "audio/l16;rate=16000",
            },
            params={
                "model": "nova-2",
                "language": "en",
                "smart_format": "true",
                "punctuate": "true",
            },
            data=bytes(audio_buffer),
            timeout=10,
        )
        
        if response.status_code != 200:
            logger.error(f"Deepgram STT error: {response.status_code} {response.text[:200]}")
            return None
        
        result = response.json()
        transcript = (
            result.get("results", {})
            .get("channels", [{}])[0]
            .get("alternatives", [{}])[0]
            .get("transcript", "")
            .strip()
        )
        
        if transcript:
            logger.info(f"Deepgram STT ({duration_seconds:.1f}s audio): \"{transcript}\"")
            return transcript
        else:
            logger.info(f"Deepgram STT: empty transcript ({duration_seconds:.1f}s audio)")
            return None
            
    except Exception as e:
        logger.error(f"Deepgram STT error: {e}")
        return None


def _send_tts_response(
    ws, 
    text: str = None,
    voice_id: str = None,
    engine: ConversationEngine = None,
    conversation_history: list = None,
    call_uuid: str = None,
    user_message: str = None
):
    """
    Generate AI response + TTS audio and send to Vonage WebSocket.
    
    Args:
        ws: WebSocket connection
        text: Direct text to speak (skips Claude if provided)
        voice_id: ElevenLabs voice clone ID
        engine: ConversationEngine instance
        conversation_history: Running conversation
        call_uuid: Call UUID for session tracking
        user_message: What the manager said (triggers Claude response)
    """
    try:
        # Get response text
        if text:
            response_text = text
        elif user_message and engine:
            conversation_history.append({"role": "user", "content": user_message})
            response_text = engine.generate_response(user_message, conversation_history)
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Save to session
            if call_uuid:
                session_manager.add_turn(call_uuid, "user", user_message)
                session_manager.add_turn(call_uuid, "assistant", response_text)
        else:
            return
        
        logger.info(f"AI: \"{response_text}\"")
        
        # Synthesize via ElevenLabs TTS
        loop = asyncio.new_event_loop()
        try:
            audio_bytes = loop.run_until_complete(
                _synthesize_and_convert(response_text, voice_id)
            )
            
            if audio_bytes:
                # Send audio in chunks (Vonage expects PCM 16kHz 16-bit LE)
                chunk_size = 640  # 20ms at 16kHz 16-bit
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    ws.send(chunk)
                
                logger.info(f"Sent {len(audio_bytes)} bytes of TTS audio")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"TTS response error: {e}", exc_info=True)


async def _synthesize_and_convert(text: str, voice_id: str = None) -> bytes:
    """
    Synthesize text to PCM 16kHz 16-bit audio via ElevenLabs.
    
    Uses the ElevenLabs REST API with output_format=pcm_16000 to get
    raw PCM audio directly compatible with Vonage WebSocket.
    """
    from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID
    import requests as req
    
    vid = voice_id or ELEVENLABS_VOICE_ID
    
    try:
        # Use REST API for simplicity and direct PCM output
        response = req.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
            headers={
                "xi-api-key": ELEVENLABS_API_KEY,
                "Content-Type": "application/json",
                "Accept": "audio/pcm",
            },
            params={
                "output_format": "pcm_16000",  # PCM 16kHz 16-bit signed LE
            },
            json={
                "text": text,
                "model_id": ELEVENLABS_MODEL_ID,
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.75,
                    "style": 0.0,
                    "use_speaker_boost": True,
                },
            },
            timeout=15,
        )
        
        if response.status_code != 200:
            logger.error(f"ElevenLabs TTS error: {response.status_code} {response.text[:200]}")
            return None
        
        audio_data = response.content
        logger.info(f"ElevenLabs TTS: synthesized {len(audio_data)} bytes of PCM audio")
        return audio_data
        
    except Exception as e:
        logger.error(f"ElevenLabs synthesis error: {e}")
        return None
