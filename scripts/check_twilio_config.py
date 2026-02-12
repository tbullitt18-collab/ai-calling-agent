"""
Check current Twilio phone number configuration.
"""
import os
from twilio.rest import Client
from dotenv import load_dotenv

def check_config():
    load_dotenv()
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    
    client = Client(sid, token)
    
    print(f"Checking configuration for {phone_number}...")
    numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
    
    if not numbers:
        print(f"Number {phone_number} not found in account.")
        return
        
    n = numbers[0]
    print(f"Number SID: {n.sid}")
    print(f"Friendly Name: {n.friendly_name}")
    print(f"Voice URL: {n.voice_url}")
    print(f"Voice Method: {n.voice_method}")
    print(f"Voice Fallback URL: {n.voice_fallback_url}")
    print(f"Status Callback URL: {n.status_callback}")

if __name__ == "__main__":
    check_config()
