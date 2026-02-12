"""
Twilio Voice API integration for Rain Check.
Handles call routing, TwiML generation, and Media Stream connections.
"""

import logging
from twilio.rest import Client

from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from app.config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, BASE_URL

# Initialize Twilio Client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

logger = logging.getLogger(__name__)

from urllib.parse import urljoin, urlencode

def generate_answer_twiml(call_sid: str) -> str:
    """
    Generate TwiML for answering an incoming call with WebSocket audio.
    Connects the call to a Media Stream.
    """
    response = VoiceResponse()
    
    # Optional greeting before stream starts
    response.say("Hello, you've reached Rain Check. Preparing your AI voice twin.")
    
    # Connect to Media Stream
    connect = Connect()
    ws_url = f"wss://{BASE_URL.replace('https://', '').replace('http://', '')}/ws/audio/{call_sid}"
    logger.info(f"Generated WebSocket URL: {ws_url}")
    
    stream = Stream(url=ws_url)
    connect.append(stream)
    response.append(connect)
    
    twiml_str = str(response)
    logger.info(f"Generated TwiML for {call_sid}:\n{twiml_str}")
    return twiml_str


def initiate_outbound_call(to_number: str, reason: str = None, notes: str = None, voice_id: str = None) -> dict:
    """
    Initiate an outbound call that connects to the AI agent.
    Includes reason, notes, and voice_id in the webhook URL for context.
    """
    
    params = {}
    if reason: params['reason'] = reason
    if notes: params['notes'] = notes
    if voice_id: params['voice_id'] = voice_id
    
    query_string = f"?{urlencode(params)}" if params else ""
    webhook_url = urljoin(BASE_URL, f"/webhook/outbound-twiml{query_string}")
    
    logger.info(f"Initiating outbound call to {to_number} with URL: {webhook_url}")
    
    call = client.calls.create(
        url=webhook_url,
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )
    return {"uuid": call.sid}
