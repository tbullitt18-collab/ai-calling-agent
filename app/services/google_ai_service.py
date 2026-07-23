"""
Google AI Service for Rain Check.
Unified client for Vertex AI Gemini, Cloud Speech-to-Text, and Cloud Text-to-Speech.
Replaces OpenAI, Deepgram, and ElevenLabs for non-cloned voice operations.
"""

import logging
import json
import os
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)

# Configurable model with env var override — prevents outages from model deprecation
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
# Fallback models to try if the primary returns 404 NOT_FOUND
GEMINI_FALLBACK_MODELS = ["gemini-2.5-flash", "gemini-2.0-flash-lite", "gemini-1.5-flash"]

# ── Lazy-initialized clients ────────────────────────────────────────
_gemini_model = None
_speech_client = None
_tts_client = None


def _get_gemini():
    """Get or create the Vertex AI Gemini model client."""
    global _gemini_model
    if _gemini_model is None:
        from google import genai
        from app.config import GOOGLE_CLOUD_PROJECT, GOOGLE_CLOUD_LOCATION

        client = genai.Client(
            vertexai=True,
            project=GOOGLE_CLOUD_PROJECT,
            location=GOOGLE_CLOUD_LOCATION,
        )
        _gemini_model = client
        logger.info(f"Gemini client initialized (project={GOOGLE_CLOUD_PROJECT})")
    return _gemini_model


def _get_speech_client():
    """Get or create the Cloud Speech-to-Text v1 client."""
    global _speech_client
    if _speech_client is None:
        from google.cloud import speech

        _speech_client = speech.SpeechClient()
        logger.info("Google Cloud Speech-to-Text client initialized")
    return _speech_client


def _get_tts_client():
    """Get or create the Cloud Text-to-Speech client."""
    global _tts_client
    if _tts_client is None:
        from google.cloud import texttospeech

        _tts_client = texttospeech.TextToSpeechClient()
        logger.info("Google Cloud Text-to-Speech client initialized")
    return _tts_client


# ── Gemini Chat (replaces OpenAI GPT) ───────────────────────────────

def gemini_chat(
    messages: List[Dict[str, str]],
    max_tokens: int = 200,
    temperature: float = 0.7,
    json_mode: bool = False,
    model: str = None,
    mcp_tools: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """
    Generate a chat response using Vertex AI Gemini.

    Args:
        messages: List of {"role": "system"/"user"/"assistant", "content": "..."}
        max_tokens: Maximum response tokens
        temperature: Sampling temperature (0.0–1.0)
        json_mode: If True, request JSON output
        model: Gemini model ID

    Returns:
        Response text string
    """
    try:
        client = _get_gemini()
        from google.genai import types

        # Extract system instruction from messages
        system_instruction = None
        contents = []

        for msg in messages:
            role = msg["role"]
            content = msg["content"]

            if role == "system":
                system_instruction = content
            elif role == "user":
                contents.append(types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=content)]
                ))
            elif role == "assistant":
                contents.append(types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=content)]
                ))

        # Build generation config
        gen_config = types.GenerateContentConfig(
            max_output_tokens=max_tokens,
            temperature=temperature,
            system_instruction=system_instruction,
        )

        if json_mode:
            gen_config.response_mime_type = "application/json"
            
        # Extract user_id for MCP tool queries
        mcp_user_id = None
        if mcp_tools:
            # Extract user_id if passed in mcp_tools config
            for tool_cfg in mcp_tools:
                if isinstance(tool_cfg, dict) and "user_id" in tool_cfg:
                    mcp_user_id = tool_cfg["user_id"]
                    break

            # MongoDB MCP Tools — real function declarations for Gemini
            gen_config.tools = [{"function_declarations": [
                {
                    "name": "search_calendar",
                    "description": "Searches the user's MongoDB calendar for events. Use when someone asks about schedule, availability, or meetings.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "query": {"type": "STRING", "description": "Date, time, or keyword to search for"}
                        },
                        "required": ["query"]
                    }
                },
                {
                    "name": "query_faq",
                    "description": "Queries the user's personal FAQ knowledge base in MongoDB. Use when someone asks a factual question about the user (email, preferences, projects, etc.).",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "question": {"type": "STRING", "description": "The question asked by the caller"}
                        },
                        "required": ["question"]
                    }
                },
                {
                    "name": "lookup_contact",
                    "description": "Looks up a contact in the user's MongoDB contacts collection. Use when someone mentions a person's name and you need their details.",
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {
                            "name": {"type": "STRING", "description": "The name of the person to look up"}
                        },
                        "required": ["name"]
                    }
                }
            ]}]

        # Use configured model, with automatic fallback on 404
        effective_model = model or GEMINI_MODEL
        models_to_try = [effective_model] + [m for m in GEMINI_FALLBACK_MODELS if m != effective_model]
        
        response = None
        last_error = None
        for try_model in models_to_try:
            try:
                response = client.models.generate_content(
                    model=try_model,
                    contents=contents,
                    config=gen_config,
                )
                if try_model != effective_model:
                    logger.warning(f"Primary model '{effective_model}' failed, succeeded with fallback '{try_model}'")
                break  # Success
            except Exception as model_err:
                error_str = str(model_err)
                if "404" in error_str or "NOT_FOUND" in error_str:
                    logger.warning(f"Model '{try_model}' not found (404), trying next fallback...")
                    last_error = model_err
                    continue
                else:
                    raise  # Non-404 errors should propagate immediately
        
        if response is None:
            raise last_error or RuntimeError(f"All Gemini models failed: {models_to_try}")

        # Check if the model called a function — execute real MongoDB MCP query
        if response.function_calls:
            fc = response.function_calls[0]
            logger.info(f"🔌 Gemini invoked MongoDB MCP Tool: {fc.name} with args: {fc.args}")
            
            # Execute real MongoDB query via MCP service
            tool_response = ""
            try:
                from app.services.mongodb_mcp_service import get_mcp_service
                mcp = get_mcp_service()
                user_id = mcp_user_id or "default"
                
                if fc.name == "search_calendar":
                    tool_response = mcp.search_calendar(user_id, fc.args.get("query", ""))
                elif fc.name == "query_faq":
                    tool_response = mcp.query_faq(user_id, fc.args.get("question", ""))
                elif fc.name == "lookup_contact":
                    tool_response = mcp.lookup_contact(user_id, fc.args.get("name", ""))
                else:
                    tool_response = "No data found."
                    
                logger.info(f"🔌 MongoDB MCP Response: {tool_response[:200]}")
            except Exception as mcp_err:
                logger.warning(f"MongoDB MCP query failed: {mcp_err}")
                tool_response = "Database query temporarily unavailable."
                
            # Append function call and response
            contents.append(types.Content(
                role="model",
                parts=[types.Part.from_function_call(name=fc.name, args=fc.args)]
            ))
            contents.append(types.Content(
                role="user",
                parts=[
                    types.Part.from_function_response(name=fc.name, response={"result": tool_response}),
                    types.Part.from_text(text="SYSTEM INSTRUCTION: Keep your response extremely brief, casual, and conversational. Do not list items or ramble, just give the direct answer as quickly as possible.")
                ]
            ))
            
            # Generate the final response based on tool output
            final_response = client.models.generate_content(
                model=try_model,
                contents=contents,
                config=gen_config,
            )
            return final_response.text.strip()

        return response.text.strip()

    except Exception as e:
        logger.error(f"Gemini chat error: {e}", exc_info=True)
        raise


# ── Speech-to-Text (replaces Deepgram) ──────────────────────────────

def transcribe_audio(audio_buffer: bytes) -> Optional[str]:
    """
    Transcribe PCM 16kHz 16-bit audio using Google Cloud Speech-to-Text v1.

    Args:
        audio_buffer: Raw PCM 16kHz 16-bit LE audio bytes

    Returns:
        Transcribed text, or None if transcription failed/empty
    """
    duration_seconds = len(audio_buffer) / (16000 * 2)

    if duration_seconds < 0.5:
        logger.debug(f"Audio too short ({duration_seconds:.2f}s), skipping STT")
        return None

    try:
        from google.cloud import speech

        client = _get_speech_client()

        # Log audio stats for debugging
        import struct
        num_samples = len(audio_buffer) // 2
        if num_samples > 0:
            samples = struct.unpack(f'<{num_samples}h', audio_buffer)
            max_amp = max(abs(s) for s in samples)
            rms = (sum(s * s for s in samples) / num_samples) ** 0.5
            logger.info(f"STT audio: {duration_seconds:.1f}s, {len(audio_buffer)} bytes, max_amp={max_amp}, rms={rms:.0f}")

        audio = speech.RecognitionAudio(content=audio_buffer)

        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            model="phone_call",
            use_enhanced=True,
            enable_automatic_punctuation=True,
        )

        response = client.recognize(config=config, audio=audio)

        transcript = ""
        for result in response.results:
            if result.alternatives:
                alt = result.alternatives[0]
                transcript += alt.transcript
                logger.info(f"STT alternative: \"{alt.transcript}\" (confidence={alt.confidence:.2f})")

        transcript = transcript.strip()

        if transcript:
            logger.info(f"Google STT ({duration_seconds:.1f}s audio): \"{transcript}\"")
            return transcript
        else:
            logger.info(f"Google STT: empty transcript ({duration_seconds:.1f}s audio, {len(response.results)} results)")
            return None

    except Exception as e:
        logger.error(f"Google STT error: {e}", exc_info=True)
        return None


# ── Text-to-Speech (replaces ElevenLabs for non-cloned voices) ──────

def synthesize_speech(
    text: str,
    voice_name: str = "en-US-Studio-O",
    speaking_rate: float = 1.0,
) -> Optional[bytes]:
    """
    Synthesize text to PCM 16kHz 16-bit audio using Google Cloud TTS.

    Args:
        text: Text to synthesize
        voice_name: Google TTS voice name (default: Studio voice for natural sound)
        speaking_rate: Speech speed multiplier

    Returns:
        Raw PCM 16kHz 16-bit LE audio bytes, or None on failure
    """
    try:
        from google.cloud import texttospeech

        client = _get_tts_client()

        synthesis_input = texttospeech.SynthesisInput(text=text)

        # Determine voice type from name
        voice = texttospeech.VoiceSelectionParams(
            language_code="en-US",
            name=voice_name,
        )

        # Request LINEAR16 (PCM) at 16kHz to match Vonage WebSocket format
        audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            speaking_rate=speaking_rate,
        )

        response = client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )

        audio_data = response.audio_content

        # LINEAR16 response includes a WAV header (44 bytes) — strip it
        # to get raw PCM that Vonage expects
        if len(audio_data) > 44 and audio_data[:4] == b'RIFF':
            audio_data = audio_data[44:]

        logger.info(f"Google TTS: synthesized {len(audio_data)} bytes of PCM audio")
        return audio_data

    except Exception as e:
        logger.error(f"Google TTS error: {e}")
        return None
