"""
Twilio Voice API integration for Rain Check.
Handles call routing, TwiML generation, and Media Stream connections.
"""

from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Connect, Stream
from config import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER, BASE_URL

# Initialize Twilio Client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def generate_answer_twiml(call_sid: str) -> str:
    """
    Generate TwiML for answering an incoming call with WebSocket audio.
    Connects the call to a Media Stream.
    """
    response = VoiceResponse()
    
    # Optional greeting before stream starts
    response.say("Hello, you've reached Rain Check. How can I help you today?")
    
    # Connect to Media Stream
    connect = Connect()
    stream = Stream(url=f"wss://{BASE_URL.replace('https://', '').replace('http://', '')}/ws/audio/{call_sid}")
    connect.append(stream)
    response.append(connect)
    
    return str(response)


def initiate_outbound_call(to_number: str) -> dict:
    """
    Initiate an outbound call that connects to the AI agent.
    """
    call = client.calls.create(
        url=f"{BASE_URL}/webhook/outbound-twiml",
        to=to_number,
        from_=TWILIO_PHONE_NUMBER
    )
    return {"uuid": call.sid}
