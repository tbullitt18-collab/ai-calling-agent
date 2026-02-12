"""
ElevenLabs Real-Time API integration for Rain Check.
Provides streaming TTS and conversational AI with sub-second latency.
"""

import asyncio
import websockets
import json
import base64
from typing import AsyncGenerator, Callable, Optional
from dataclasses import dataclass

# Lazy initialization
_api_key = None
_voice_id = None
_model_id = None


def _load_config():
    """Load configuration lazily."""
    global _api_key, _voice_id, _model_id
    if _api_key is None:
        from app.config import ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID, ELEVENLABS_MODEL_ID
        _api_key = ELEVENLABS_API_KEY
        _voice_id = ELEVENLABS_VOICE_ID
        _model_id = ELEVENLABS_MODEL_ID


@dataclass
class VoiceSettings:
    """Voice synthesis settings."""
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    use_speaker_boost: bool = True


class ElevenLabsRealtimeClient:
    """
    WebSocket client for ElevenLabs real-time voice synthesis.
    
    Supports both text-to-speech streaming and conversational AI modes.
    """
    
    TTS_WS_URL = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
    CONVAI_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"
    
    def __init__(
        self,
        voice_id: str = None,
        model_id: str = None,
        voice_settings: VoiceSettings = None
    ):
        """
        Initialize ElevenLabs client.
        
        Args:
            voice_id: Override default voice ID
            model_id: Override default model ID
            voice_settings: Voice synthesis settings
        """
        _load_config()
        self.voice_id = voice_id or _voice_id
        self.model_id = model_id or _model_id
        self.voice_settings = voice_settings or VoiceSettings()
        self.ws = None
        self._audio_queue = asyncio.Queue()
        
    async def connect_tts(self) -> None:
        """Establish WebSocket connection for TTS streaming."""
        url = self.TTS_WS_URL.format(voice_id=self.voice_id)
        url += f"?model_id={self.model_id}"
        
        headers = {
            "xi-api-key": _api_key
        }
        
        self.ws = await websockets.connect(url, additional_headers=headers)
        
        # Send initial configuration
        await self.ws.send(json.dumps({
            "text": " ",  # Initial space to start stream
            "voice_settings": {
                "stability": self.voice_settings.stability,
                "similarity_boost": self.voice_settings.similarity_boost,
                "style": self.voice_settings.style,
                "use_speaker_boost": self.voice_settings.use_speaker_boost
            },
            "generation_config": {
                "chunk_length_schedule": [120, 160, 250, 290]
            },
            "xi_api_key": _api_key
        }))
        
    async def connect_conversational(self, conversation_config: dict = None) -> None:
        """
        Establish WebSocket connection for conversational AI.
        
        Args:
            conversation_config: Optional dynamic overrides for the conversation
                                (e.g., system_prompt_override, initial_message)
        """
        headers = {
            "xi-api-key": _api_key
        }
        
        self.ws = await websockets.connect(
            f"{self.CONVAI_WS_URL}?model_id={self.model_id}",
            additional_headers=headers
        )
        
        # Build configuration message
        config_msg = {
            "type": "conversation.config",
            "voice_id": self.voice_id,
            "output_format": "ulaw_8000" # Match Twilio format
        }
        
        if conversation_config:
            config_msg["conversation_config"] = conversation_config
            
        # Send initial configuration
        await self.ws.send(json.dumps(config_msg))

        
    async def send_text_chunk(self, text: str, flush: bool = False) -> None:
        """
        Send a text chunk for TTS synthesis.
        
        Args:
            text: Text to synthesize
            flush: Whether to flush the buffer and finalize
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected. Call connect_tts() first.")
            
        message = {"text": text}
        if flush:
            message["flush"] = True
            
        await self.ws.send(json.dumps(message))
        
    async def send_audio_input(self, audio_chunk: bytes) -> None:
        """
        Send audio chunk for speech-to-text processing (conversational mode).
        
        Args:
            audio_chunk: Raw audio bytes (PCM 16kHz)
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected. Call connect_conversational() first.")
            
        await self.ws.send(json.dumps({
            "type": "audio.input",
            "audio": base64.b64encode(audio_chunk).decode()
        }))
        
    async def receive_audio_stream(self) -> AsyncGenerator[bytes, None]:
        """
        Receive streaming audio chunks from TTS synthesis.
        
        Yields:
            Audio bytes (MP3 format for TTS, PCM for conversational)
        """
        if not self.ws:
            return
            
        async for message in self.ws:
            try:
                data = json.loads(message)
                
                # TTS stream format
                if "audio" in data and data["audio"]:
                    audio_bytes = base64.b64decode(data["audio"])
                    yield audio_bytes
                    
                # Check for completion
                if data.get("isFinal", False):
                    break
                    
            except json.JSONDecodeError:
                # Binary audio data
                yield message
                
    async def receive_conversational_responses(self) -> AsyncGenerator[dict, None]:
        """
        Receive streaming responses from conversational AI.
        
        Yields:
            Response dictionaries with type, transcript, or audio
        """
        if not self.ws:
            return
            
        async for message in self.ws:
            try:
                data = json.loads(message)
                yield data
                
                # Handle different response types
                if data.get("type") == "conversation.end":
                    break
                    
            except json.JSONDecodeError:
                continue
                
    async def synthesize_text(
        self,
        text: str,
        on_audio_chunk: Callable[[bytes], None] = None
    ) -> bytes:
        """
        Synthesize text to speech with streaming.
        
        Args:
            text: Full text to synthesize
            on_audio_chunk: Optional callback for each audio chunk
            
        Returns:
            Complete audio bytes
        """
        if not self.ws:
            await self.connect_tts()
            
        # Send text with flush
        await self.send_text_chunk(text, flush=True)
        
        # Send EOS (end-of-stream) signal — required by ElevenLabs
        # An empty string tells the server no more text is coming
        await self.ws.send(json.dumps({"text": ""}))
        
        # Collect audio
        audio_parts = []
        async for chunk in self.receive_audio_stream():
            audio_parts.append(chunk)
            if on_audio_chunk:
                on_audio_chunk(chunk)
                
        return b"".join(audio_parts)
        
    async def close(self) -> None:
        """Close WebSocket connection."""
        if self.ws:
            # Send end of stream message
            try:
                await self.ws.send(json.dumps({"text": ""}))
            except:
                pass
            await self.ws.close()
            self.ws = None


async def synthesize_speech_async(
    text: str,
    voice_id: str = None,
    model_id: str = None
) -> bytes:
    """
    Convenience function to synthesize text to speech.
    
    Args:
        text: Text to synthesize
        voice_id: Optional voice ID override
        model_id: Optional model ID override
        
    Returns:
        Audio bytes
    """
    client = ElevenLabsRealtimeClient(voice_id=voice_id, model_id=model_id)
    try:
        await client.connect_tts()
        return await client.synthesize_text(text)
    finally:
        await client.close()


def synthesize_speech_sync(
    text: str,
    voice_id: str = None,
    model_id: str = None
) -> bytes:
    """
    Synchronous wrapper for speech synthesis.
    
    Args:
        text: Text to synthesize
        voice_id: Optional voice ID override
        model_id: Optional model ID override
        
    Returns:
        Audio bytes
    """
    return asyncio.run(synthesize_speech_async(text, voice_id, model_id))
