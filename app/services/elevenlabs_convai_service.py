"""
ElevenLabs Conversational AI WebSocket Bridge for Rain Check.

This service bridges Vonage's inbound phone audio (PCM 16kHz 16-bit)
with ElevenLabs' Conversational AI WebSocket API.

Architecture:
  Vonage WS <--> ElevenLabsConvAIBridge <--> ElevenLabs ConvAI WS

The bridge:
1. Opens a WebSocket to ElevenLabs ConvAI with the agent_id
2. Streams inbound Vonage PCM audio to ElevenLabs as base64 audio_chunk events
3. Receives ElevenLabs audio response events and queues PCM back to Vonage
4. Handles interruption, ping/pong, and agent_response lifecycle events
5. Supports custom client_tools for MongoDB (calendar, FAQ, contacts)
"""

import asyncio
import base64
import json
import logging
import threading
import queue
import time

logger = logging.getLogger(__name__)


class ElevenLabsConvAIBridge:
    """
    Bridges Vonage PCM audio to ElevenLabs Conversational AI WebSocket.
    
    Usage (synchronous, runs in its own thread):
        bridge = ElevenLabsConvAIBridge(
            agent_id="your_agent_id",
            api_key="iams_live_...",
            outbound_queue=queue.Queue(),
            system_prompt_override="...",
            caller_phone="14045550000",
            user_id="demo_user_001",
        )
        bridge.start()            # non-blocking — starts background thread
        bridge.send_audio(pcm)    # call from Vonage WS receive loop
        bridge.stop()             # call when Vonage WS closes
    """

    CONVAI_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"

    def __init__(
        self,
        agent_id: str,
        api_key: str,
        outbound_queue: queue.Queue,
        system_prompt_override: str = None,
        caller_phone: str = None,
        user_id: str = "default",
    ):
        self.agent_id = agent_id
        self.api_key = api_key
        self.outbound_queue = outbound_queue
        self.system_prompt_override = system_prompt_override
        self.caller_phone = caller_phone
        self.user_id = user_id

        self._inbound_queue = queue.Queue()  # PCM chunks from Vonage
        self._loop = None
        self._ws = None
        self._thread = None
        self._stop_event = threading.Event()
        self._connected = threading.Event()

    # ── Public API (called from Vonage WS thread) ─────────────────────

    def start(self):
        """Start the ConvAI bridge in a background thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        # Wait up to 5 seconds for connection
        if not self._connected.wait(timeout=5.0):
            logger.warning("ElevenLabs ConvAI did not connect within 5s")

    def send_audio(self, pcm_bytes: bytes):
        """Queue a PCM audio chunk from Vonage to be sent to ElevenLabs."""
        if not self._stop_event.is_set():
            self._inbound_queue.put(pcm_bytes)

    def stop(self):
        """Gracefully stop the bridge."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    # ── Internal async loop ────────────────────────────────────────────

    def _run(self):
        """Entry point for the background thread."""
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        try:
            self._loop.run_until_complete(self._async_bridge())
        except Exception as e:
            logger.error(f"ConvAI bridge crashed: {e}", exc_info=True)
        finally:
            self._loop.close()

    async def _async_bridge(self):
        """Main async coroutine — connects to ElevenLabs and runs send/receive loops."""
        try:
            import websockets
        except ImportError:
            logger.error("websockets package not installed. Run: pip install websockets")
            return

        url = f"{self.CONVAI_WS_URL}?agent_id={self.agent_id}"
        headers = {"xi-api-key": self.api_key}

        logger.info(f"Connecting to ElevenLabs ConvAI: agent_id={self.agent_id}")

        try:
            async with websockets.connect(url, additional_headers=headers) as ws:
                self._ws = ws
                logger.info("ElevenLabs ConvAI WebSocket connected")

                # Send conversation_initiation_client_data to configure the agent
                await self._send_init_config(ws)
                self._connected.set()

                # Run send and receive loops concurrently
                await asyncio.gather(
                    self._send_loop(ws),
                    self._receive_loop(ws),
                )
        except Exception as e:
            logger.error(f"ConvAI WebSocket error: {e}", exc_info=True)
        finally:
            self._connected.clear()
            logger.info("ElevenLabs ConvAI WebSocket closed")

    async def _send_init_config(self, ws):
        """
        Send the conversation_initiation_client_data message.
        This overrides the system prompt and registers client tools.
        """
        config = {
            "type": "conversation_initiation_client_data",
        }

        if self.system_prompt_override:
            config["conversation_config_override"] = {
                "agent": {
                    "prompt": {
                        "prompt": self.system_prompt_override
                    }
                }
            }

        # Register MongoDB-backed client tools
        config["custom_llm_extra_body"] = {}

        await ws.send(json.dumps(config))
        logger.info("Sent ConvAI init config")

    async def _send_loop(self, ws):
        """
        Reads PCM chunks from the inbound queue and streams them to ElevenLabs.
        Vonage sends PCM 16kHz 16-bit LE — ElevenLabs ConvAI expects base64 PCM.
        """
        loop = asyncio.get_event_loop()

        while not self._stop_event.is_set():
            try:
                # Non-blocking check for audio from Vonage
                pcm = await loop.run_in_executor(
                    None,
                    lambda: self._inbound_queue.get(timeout=0.05)
                )
                # Encode and send
                audio_b64 = base64.b64encode(pcm).decode("utf-8")
                await ws.send(json.dumps({
                    "user_audio_chunk": audio_b64
                }))
            except Exception:
                # queue.Empty or timeout — just loop
                await asyncio.sleep(0.01)

        # Signal end of audio to ElevenLabs
        try:
            await ws.close()
        except Exception:
            pass

    async def _receive_loop(self, ws):
        """
        Receives messages from ElevenLabs and routes to appropriate handlers.
        """
        async for raw_message in ws:
            if self._stop_event.is_set():
                break

            try:
                msg = json.loads(raw_message)
                msg_type = msg.get("type", "")

                if msg_type == "audio":
                    await self._handle_audio(msg)

                elif msg_type == "agent_response":
                    text = msg.get("agent_response_event", {}).get("agent_response", "")
                    if text:
                        logger.info(f"ElevenLabs agent said: '{text}'")

                elif msg_type == "user_transcript":
                    text = msg.get("user_transcription_event", {}).get("user_transcript", "")
                    if text:
                        logger.info(f"Caller said: '{text}'")

                elif msg_type == "interruption":
                    logger.info("ElevenLabs: interruption detected — clearing audio queue")
                    self._clear_outbound_queue()

                elif msg_type == "ping":
                    event_id = msg.get("ping_event", {}).get("event_id")
                    await ws.send(json.dumps({
                        "type": "pong",
                        "event_id": event_id
                    }))

                elif msg_type == "conversation_initiation_metadata":
                    meta = msg.get("conversation_initiation_metadata_event", {})
                    logger.info(f"ConvAI session started: conversation_id={meta.get('conversation_id')}")

                elif msg_type == "client_tool_call":
                    await self._handle_tool_call(ws, msg)

                elif msg_type in ("internal_tentative_agent_response",):
                    pass  # Ignore tentative responses

                else:
                    logger.debug(f"ConvAI unhandled message type: {msg_type}")

            except json.JSONDecodeError:
                logger.warning(f"ConvAI non-JSON message: {raw_message[:100]}")
            except Exception as e:
                logger.error(f"ConvAI receive error: {e}", exc_info=True)

    async def _handle_audio(self, msg):
        """Decode ElevenLabs audio and put PCM chunks into outbound queue for Vonage."""
        audio_event = msg.get("audio_event", {})
        audio_b64 = audio_event.get("audio_base_64", "")

        if audio_b64:
            try:
                pcm_bytes = base64.b64decode(audio_b64)
                # Send in 20ms chunks (640 bytes at 16kHz 16-bit)
                chunk_size = 640
                for i in range(0, len(pcm_bytes), chunk_size):
                    self.outbound_queue.put(pcm_bytes[i:i + chunk_size])
            except Exception as e:
                logger.error(f"Failed to decode ElevenLabs audio: {e}")

    async def _handle_tool_call(self, ws, msg):
        """
        Handle client tool calls from ElevenLabs ConvAI.
        Routes to MongoDB MCP service (calendar, FAQ, contacts).
        """
        tool_call = msg.get("client_tool_call", {})
        tool_name = tool_call.get("tool_name", "")
        tool_call_id = tool_call.get("tool_call_id", "")
        parameters = tool_call.get("parameters", {})

        logger.info(f"ConvAI tool call: {tool_name}({parameters})")

        result = "Tool not found."
        is_error = False

        try:
            from app.services.mongodb_mcp_service import get_mcp_service
            mcp = get_mcp_service()

            if tool_name == "search_calendar":
                result = mcp.search_calendar(self.user_id, parameters.get("query", ""))
            elif tool_name == "query_faq":
                result = mcp.query_faq(self.user_id, parameters.get("question", ""))
            elif tool_name == "lookup_contact":
                result = mcp.lookup_contact(self.user_id, parameters.get("name", ""))
            elif tool_name == "book_calendar":
                result = mcp.book_calendar(
                    self.user_id,
                    parameters.get("title", "Meeting"),
                    parameters.get("date", "TBD"),
                    parameters.get("description", "")
                )
            elif tool_name == "send_sms":
                from app.services.vonage_service import send_sms
                result = send_sms(
                    parameters.get("to_number", self.caller_phone or ""),
                    parameters.get("text", "")
                )
            else:
                result = f"Unknown tool: {tool_name}"
                is_error = True

        except Exception as e:
            logger.error(f"Tool call error: {e}")
            result = f"Error executing {tool_name}: {str(e)}"
            is_error = True

        # Send tool result back to ElevenLabs
        await ws.send(json.dumps({
            "type": "client_tool_result",
            "tool_call_id": tool_call_id,
            "result": result,
            "is_error": is_error
        }))
        logger.info(f"Tool result sent: {result[:100]}")

    def _clear_outbound_queue(self):
        """Drain the outbound queue to stop playing audio on interruption."""
        while not self.outbound_queue.empty():
            try:
                self.outbound_queue.get_nowait()
            except Exception:
                break
