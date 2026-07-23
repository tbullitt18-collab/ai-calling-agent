"""
Vonage Audio Streaming and Webhook routes for Rain Check.
Bridges Vonage WebSocket ↔ Gemini (conversation) ↔ Google TTS / ElevenLabs.
"""

import json
import os
import struct
import logging
import asyncio
import io
import time
from flask import Blueprint, request, jsonify
from app import sock
from app.services.vonage_service import generate_answer_ncco, generate_error_ncco
from app.models.call_session import SessionManager, get_session_manager
from app.services.conversation_service import ConversationEngine, AgentPersona

logger = logging.getLogger(__name__)
audio_bp = Blueprint('audio', __name__)

session_manager = get_session_manager()


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
            from app.models.call_session import get_session_manager
            
            call_logger = get_call_logger()
            sm = get_session_manager()
            
            # Fetch transcript from session manager
            transcript = sm.get_conversation_history(uuid)
            summary = call_logger._generate_summary(transcript) if transcript else "No conversation recorded."

            if call_logger.calls is not None:
                call_logger.calls.update_one(
                    {"call_uuid": uuid},
                    {"$set": {
                        "status": status,
                        "end_reason": data.get('reason', ''),
                        "duration_seconds": int(duration) if duration else 0,
                        "transcript": transcript,
                        "summary": summary
                    }},
                    upsert=True
                )
                logger.info(f"Call event logged to MongoDB: {uuid} → {status}")
                
            # Clean up session
            sm.delete_session(uuid)
        except Exception as e:
            logger.warning(f"Failed to log call event to MongoDB: {e}")
    
    return '', 204


# ── Audio Processing Helpers ─────────────────────────────────────────

def pcm16_to_float(pcm_bytes: bytes) -> list:
    """Convert PCM 16-bit signed LE audio to float samples."""
    samples = struct.unpack(f'<{len(pcm_bytes)//2}h', pcm_bytes)
    return [s / 32768.0 for s in samples]


def _compute_rms(pcm_bytes: bytes) -> float:
    """Compute RMS energy of a PCM 16-bit audio chunk."""
    if len(pcm_bytes) < 2:
        return 0.0
    samples = pcm16_to_float(pcm_bytes)
    return (sum(s * s for s in samples) / len(samples)) ** 0.5


def _has_speech(pcm_bytes: bytes, threshold: float = 0.015) -> bool:
    """Check if a PCM audio chunk contains speech energy above threshold."""
    return _compute_rms(pcm_bytes) > threshold


def _tail_is_silent(pcm_bytes: bytes, threshold: float = 0.015, tail_ms: int = 1200) -> bool:
    """
    Check if the tail end of a buffer is silent.
    tail_ms: how many milliseconds of silence at the end to require.
    """
    tail_bytes = int(16000 * 2 * tail_ms / 1000)  # 16kHz, 16-bit = 2 bytes/sample
    if len(pcm_bytes) < tail_bytes:
        return False
    tail = pcm_bytes[-tail_bytes:]
    rms = _compute_rms(tail)
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
    
    Speech detection state machine:
      IDLE → speech energy detected → SPEAKING (start buffering)
      SPEAKING → tail silence detected → process buffer (STT → GPT → TTS)
      After processing → back to IDLE
    """
    logger.info(f"WebSocket connected: {call_uuid}")
    
    # Load call context
    context = session_manager.get_context(call_uuid) or {}
    reason = context.get('reason', 'calling in')
    notes = context.get('notes', '')
    voice_id = context.get('voice_id')
    
    # Track the authenticated user for MongoDB MCP queries
    call_user_id = context.get('user_id', 'default')
    
    # Load the user's permanent display name for AI identity.
    # This is who the AI says it is when asked "Who is this?"
    represented_user = "the user"
    
    # First try: get the permanent display name from user_profiles
    try:
        from app.models.user_profile import UserProfile
        user_profile_model = UserProfile()
        # Find by the voice_id's owner (look up the voice profile to get user_id)
        if voice_id:
            from app.models.voice_profile import VoiceProfile
            vp_model = VoiceProfile()
            voice_prof = vp_model.get_profile(voice_id)
            if voice_prof:
                owner_username = voice_prof.get('user_id', 'default')
                user_prof = user_profile_model.get_profile(owner_username)
                if user_prof and user_prof.get('display_name'):
                    represented_user = user_prof['display_name']
                    logger.info(f"Using permanent display name: {represented_user}")
    except Exception as e:
        logger.warning(f"Failed to load display name: {e}")
    
    # Fallback: if no display name found, use voice profile name
    if represented_user == "the user" and voice_id:
        try:
            from app.models.voice_profile import VoiceProfile
            profile_model = VoiceProfile()
            prof = profile_model.get_profile(voice_id)
            if prof and prof.get('name'):
                represented_user = prof.get('name')
        except Exception as e:
            logger.warning(f"Failed to load profile name for {voice_id}: {e}")

    # Load workplace setup to give AI twin factual context
    setup_context = ""
    try:
        if represented_user != "the user":
            from app.models.user_profile import UserProfile
            _up_model = UserProfile()
            # Find by voice owner or by the resolved username
            _owner = None
            if voice_id:
                from app.models.voice_profile import VoiceProfile
                _vp = VoiceProfile()
                _vprof = _vp.get_profile(voice_id)
                if _vprof:
                    _owner = _vprof.get('user_id', 'default')
            if _owner:
                _up = _up_model.get_profile(_owner)
                if _up and _up.get('setup'):
                    setup = _up['setup']
                    parts = []
                    if setup.get('employee_id'):
                        parts.append(f"Employee ID: {setup['employee_id']}")
                    if setup.get('company_name'):
                        parts.append(f"Company: {setup['company_name']}")
                    if setup.get('department'):
                        parts.append(f"Department: {setup['department']}")
                    if setup.get('position'):
                        parts.append(f"Position: {setup['position']}")
                    if setup.get('manager_name'):
                        parts.append(f"Manager's name: {setup['manager_name']}")
                    if setup.get('shift_start') and setup.get('shift_end'):
                        parts.append(f"Shift: {setup['shift_start']} - {setup['shift_end']}")
                    if setup.get('work_days'):
                        parts.append(f"Work days: {', '.join(setup['work_days'])}")
                    if parts:
                        setup_context = " | ".join(parts)
                        logger.info(f"Loaded workplace setup for call context")
    except Exception as e:
        logger.warning(f"Failed to load workplace setup: {e}")

    # ── IBM Bob Legal Intake Mode ──────────────────────────────────────
    if reason == 'legal_intake':
        # Load the legal intake system prompt from the knowledge base file
        _legal_prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            'ibm_bob_legal_prompt.txt'
        )
        try:
            with open(_legal_prompt_path, 'r', encoding='utf-8') as _f:
                _legal_custom = _f.read()
        except FileNotFoundError:
            logger.error(f"Legal intake prompt not found at {_legal_prompt_path}")
            _legal_custom = ""
        
        persona = AgentPersona(
            name="Todd Bullitt",
            role="disaster survivor applicant",
            represented_user="Todd Bullitt",
            tone="intelligent, distressed but articulate and factual",
            custom_instructions=_legal_custom
        )
        engine = ConversationEngine(persona=persona)
        # Override the system prompt entirely for legal intake
        engine.system_prompt = _legal_custom
        conversation_history = []
        logger.info("IBM BOB LEGAL INTAKE MODE ACTIVATED")
    else:
        # Build persona with call context + workplace setup
        full_context = f"You are calling to report: {reason}. "
        if setup_context:
            full_context += f"YOUR WORKPLACE INFO (use when asked): {setup_context}. "
        full_context += (
            f"CRITICAL MEMORY FILES/NOTES: '{notes}'. "
            f"If you are asked any specific factual questions (like your employee ID, shift details, or return date), strictly reference your workplace info and notes. "
            f"NEVER BREAK CHARACTER. NEVER mention being an AI, looking up a database, or checking your system. "
            f"If you don't know the answer to something you should know (like your manager's name), act flustered and human. Say something like 'Oh man, my mind just went totally blank for a second, sorry' or 'Wow, I'm drawing a complete blank right now, I'm really flustered.' "
            f"Be brief, casual, and professional."
        )

        persona = AgentPersona(
            represented_user=represented_user,
            custom_instructions=full_context
        )
        engine = ConversationEngine(persona=persona)
        conversation_history = []
    
    # Speech state machine
    audio_buffer = bytearray()
    is_speaking = False  # True when we've detected speech and are buffering
    
    # Echo suppression: after sending TTS audio, ignore incoming audio
    # for the duration of playback + margin so the AI doesn't hear itself
    state = {"echo_suppress_until": 0.0}  # timestamp when suppression ends
    ECHO_MARGIN_SECS = 0.15    # extra margin after TTS playback ends
    
    # Thresholds
    SPEECH_THRESHOLD = 0.015   # RMS above this = speech detected
    MIN_SPEECH_SECS = 0.5      # Minimum speech duration before STT
    MAX_BUFFER_SECS = 10.0     # Safety limit to prevent unbounded growth
    TAIL_SILENCE_MS = 450      # ms of silence at tail to end utterance
    
    logger.info(f"Call context — Reason: {reason}, Voice: {voice_id}")
    
    try:
        import queue
        outbound_queue = queue.Queue()
        
        # Main audio receive loop
        while True:
            # Drain queue and send before blocking on receive
            while not outbound_queue.empty():
                try:
                    chunk_to_send = outbound_queue.get_nowait()
                    ws.send(chunk_to_send)
                except Exception as e:
                    logger.error(f"Error sending queued audio: {e}")
                    raise
                    
            try:
                # Use a small timeout so we can loop around and check the queue frequently
                message = ws.receive(timeout=0.05)
            except Exception as e:
                # ConnectionClosed is caught by the outer try/except
                raise e
                
            if message is None:
                # Just a timeout
                continue
            
            # Vonage sends binary PCM audio or text control messages
            if isinstance(message, bytes):
                chunk = message
                
                # ── Echo suppression: drop audio while our own TTS is playing ──
                if time.time() < state["echo_suppress_until"]:
                    continue
                
                buf_secs = len(audio_buffer) / (16000 * 2)
                
                if not is_speaking:
                    # ── IDLE state: waiting for speech to start ──
                    if _has_speech(chunk, SPEECH_THRESHOLD):
                        is_speaking = True
                        audio_buffer.clear()
                        audio_buffer.extend(chunk)
                        logger.info("Speech started (energy detected)")
                else:
                    # ── SPEAKING state: buffering audio ──
                    audio_buffer.extend(chunk)
                    buf_secs = len(audio_buffer) / (16000 * 2)
                    
                    # Log buffer growth periodically (~every 1s)
                    if len(audio_buffer) % 32000 < len(chunk):
                        logger.info(f"Buffering speech: {len(audio_buffer)} bytes ({buf_secs:.1f}s)")
                    
                    # Check for end of speech (tail silence) or max buffer
                    should_process = False
                    
                    if buf_secs >= MAX_BUFFER_SECS:
                        logger.info(f"Max buffer reached ({buf_secs:.1f}s), processing")
                        should_process = True
                    elif buf_secs >= MIN_SPEECH_SECS and _tail_is_silent(bytes(audio_buffer), SPEECH_THRESHOLD, TAIL_SILENCE_MS):
                        logger.info(f"Speech ended (silence detected): {len(audio_buffer)} bytes ({buf_secs:.1f}s)")
                        should_process = True
                    
                    if should_process:
                        # Copy the buffer to process in background
                        buf_copy = bytearray(audio_buffer)
                        
                        def process_utterance(audio_data):
                            logger.info("Sending to Google STT...")
                            manager_text = _transcribe_audio(audio_data)
                            
                            if manager_text:
                                logger.info(f"STT result: '{manager_text}' — streaming to Gemini+TTS...")
                                from app.services.streaming_pipeline import stream_response_to_audio
                                tts_bytes_sent = stream_response_to_audio(
                                    outbound_queue=outbound_queue,
                                    voice_id=voice_id,
                                    engine=engine,
                                    conversation_history=conversation_history,
                                    call_uuid=call_uuid,
                                    user_message=manager_text,
                                    user_id=call_user_id,
                                    session_manager=session_manager,
                                )
                                # Set echo suppression window based on TTS playback length
                                if tts_bytes_sent and tts_bytes_sent > 0:
                                    playback_secs = tts_bytes_sent / (16000 * 2)
                                    state["echo_suppress_until"] = time.time() + playback_secs + ECHO_MARGIN_SECS
                                    logger.info(f"Echo suppression active for {playback_secs + ECHO_MARGIN_SECS:.1f}s")
                            else:
                                logger.info("STT returned empty — skipping (likely background noise)")
                                
                        import threading
                        threading.Thread(target=process_utterance, args=(buf_copy,)).start()
                        
                        # Reset state machine
                        audio_buffer.clear()
                        is_speaking = False
            
            elif isinstance(message, str):
                # Vonage text control messages
                try:
                    data = json.loads(message)
                    event = data.get('event')
                    if event == 'websocket:connected':
                        logger.info("Vonage WebSocket handshake complete")
                        
                        # Generate natural-sounding opening line
                        import random
                        
                        name = represented_user if represented_user != "the user" else ""
                        
                        if reason == 'legal_intake':
                            # IBM Bob Legal Intake — exact Node 1 opener
                            openers = [
                                "Hello, I am Todd Bullitt. I am calling to open an emergency legal intake regarding my FEMA disaster file number 630596501, Disaster DR-4782-KY. My situation is critical, and I need a disaster relief attorney to evaluate a federal Administrative Procedure Act claim against FEMA for Unreasonable Agency Delay and Constructive Denial."
                            ]
                        elif reason and reason.lower() not in ('calling in', 'none', ''):
                            # Calling with a specific reason — sound like a real person
                            reason_lower = reason.lower()
                            openers = [
                                f"Hey, it's {name}. So um, I'm calling because I need to take a {reason_lower}.",
                                f"Hi, yeah this is {name}. I wanted to let you know I gotta call out — {reason_lower}.",
                                f"Hey it's {name}. Um, so I'm not gonna be able to make it in today, {reason_lower}.",
                                f"Hi, this is {name} — yeah so I need to take a {reason_lower} today.",
                            ] if name else [
                                f"Hey, um, I'm calling to let you know I need a {reason_lower}.",
                                f"Hi yeah, so I wanted to call and say I gotta take a {reason_lower}.",
                            ]
                        else:
                            # Generic call — casual opener
                            openers = [
                                f"Hey, it's {name}. Can you hear me alright?",
                                f"Hi, yeah this is {name}. Hey, so um —",
                                f"Hey it's {name}, how's it going?",
                            ] if name else [
                                "Hey, can you hear me okay?",
                                "Hi, yeah — hey, so um —",
                            ]
                        
                        initial_greeting = random.choice(openers)
                        logger.info(f"Sending natural initial greeting: {initial_greeting}")
                        
                        # Add to history so AI remembers it spoke first
                        conversation_history.append({"role": "assistant", "content": initial_greeting})
                        if call_uuid:
                            session_manager.add_turn(call_uuid, "assistant", initial_greeting)
                            
                        # Send the greeting out to the user's phone
                        tts_bytes_sent = _send_tts_response(
                            outbound_queue, text=initial_greeting, voice_id=voice_id,
                            engine=None, conversation_history=None, call_uuid=None
                        )
                        # Suppress echo for the duration of the greeting playback
                        if tts_bytes_sent and tts_bytes_sent > 0:
                            playback_secs = tts_bytes_sent / (16000 * 2)
                            state["echo_suppress_until"] = time.time() + playback_secs + ECHO_MARGIN_SECS
                            logger.info(f"Greeting echo suppression for {playback_secs + ECHO_MARGIN_SECS:.1f}s")
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
    Transcribe audio using Google Cloud Speech-to-Text.
    
    Sends PCM 16kHz 16-bit audio to Google Cloud STT
    and returns the transcription text.
    
    Args:
        audio_buffer: Raw PCM 16kHz 16-bit LE audio bytes
        
    Returns:
        Transcribed text, or None if transcription failed/empty
    """
    from app.services.google_ai_service import transcribe_audio
    return transcribe_audio(bytes(audio_buffer))


def _send_tts_response(
    outbound_queue, 
    text: str = None,
    voice_id: str = None,
    engine: ConversationEngine = None,
    conversation_history: list = None,
    call_uuid: str = None,
    user_message: str = None,
    user_id: str = None
):
    """
    Generate AI response + TTS audio and queue it to be sent to Vonage WebSocket.
    
    Args:
        outbound_queue: Queue to put the audio chunks in
        text: Direct text to speak (skips AI if provided)
        voice_id: Voice ID (ElevenLabs cloned or Google system voice)
        engine: ConversationEngine instance
        conversation_history: Running conversation
        call_uuid: Call UUID for session tracking
        user_message: What the manager said (triggers Gemini response)
        user_id: Username for MongoDB MCP queries
    """
    total_bytes_sent = 0
    try:
        # Get response text
        if text:
            response_text = text
        elif user_message and engine:
            conversation_history.append({"role": "user", "content": user_message})
            response_text = engine.generate_response(user_message, conversation_history, user_id=user_id)
            conversation_history.append({"role": "assistant", "content": response_text})
            
            # Save to session
            if call_uuid:
                session_manager.add_turn(call_uuid, "user", user_message)
                session_manager.add_turn(call_uuid, "assistant", response_text)
        else:
            return 0
        
        logger.info(f"AI: \"{response_text}\"")
        
        # Synthesize TTS audio
        loop = asyncio.new_event_loop()
        try:
            audio_bytes = loop.run_until_complete(
                _synthesize_and_convert(response_text, voice_id)
            )
            
            if audio_bytes:
                total_bytes_sent = len(audio_bytes)
                # Send audio in chunks (Vonage expects PCM 16kHz 16-bit LE)
                chunk_size = 640  # 20ms at 16kHz 16-bit
                for i in range(0, len(audio_bytes), chunk_size):
                    chunk = audio_bytes[i:i + chunk_size]
                    outbound_queue.put(chunk)
                
                logger.info(f"Queued {total_bytes_sent} bytes of TTS audio")
        finally:
            loop.close()
            
    except Exception as e:
        logger.error(f"TTS response error: {e}", exc_info=True)
    
    return total_bytes_sent


async def _synthesize_and_convert(text: str, voice_id: str = None) -> bytes:
    """
    Synthesize text to PCM 16kHz 16-bit audio.
    
    Routes to the appropriate TTS engine:
    - Google system voices (en-US-*): Google Cloud TTS
    - ElevenLabs cloned voices: ElevenLabs TTS API
    - Fallback: Google Cloud TTS Studio voice
    """
    try:
        # Route 1: Google system voice (starts with "en-")
        if voice_id and voice_id.startswith("en-"):
            from app.services.google_ai_service import synthesize_speech
            audio_data = synthesize_speech(text, voice_name=voice_id)
            if audio_data:
                return audio_data
        
        # Route 2: ElevenLabs cloned voice (any non-system voice ID from ElevenLabs)
        elif voice_id and not voice_id.startswith("en-"):
            logger.info(f"🎤 Using ElevenLabs TTS for cloned voice: {voice_id}")
            try:
                import httpx
                from app.config import ELEVENLABS_API_KEY
                
                # ElevenLabs REST API for TTS — returns raw audio
                # CRITICAL: output_format MUST be a query parameter, not in the JSON body
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                headers = {
                    "xi-api-key": ELEVENLABS_API_KEY,
                    "Content-Type": "application/json"
                }
                payload = {
                    "text": text,
                    "model_id": "eleven_turbo_v2_5",
                    "voice_settings": {
                        "stability": 0.35,
                        "similarity_boost": 0.80,
                        "style": 0.45,
                        "use_speaker_boost": True
                    }
                }
                
                resp = httpx.post(url, headers=headers, json=payload, params={"output_format": "pcm_16000"}, timeout=15.0)
                
                if resp.status_code == 200:
                    audio_data = resp.content
                    logger.info(f"🎤 ElevenLabs TTS: synthesized {len(audio_data)} bytes of PCM audio")
                    return audio_data
                else:
                    logger.warning(f"ElevenLabs TTS failed ({resp.status_code}): {resp.text[:200]}")
                    # Fall through to Google TTS fallback
            except Exception as el_err:
                logger.warning(f"ElevenLabs TTS error, falling back to Google: {el_err}")
                # Fall through to Google TTS fallback
        
        # Fallback: Google Cloud TTS with default Studio voice
        from app.services.google_ai_service import synthesize_speech
        audio_data = synthesize_speech(text, voice_name="en-US-Studio-O")
        if audio_data:
            return audio_data
        
        logger.error("All TTS engines returned None")
        return b""
    except Exception as e:
        logger.error(f"TTS synthesis failed: {e}")
        return b""
