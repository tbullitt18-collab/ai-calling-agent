"""
Update Twilio Incoming Phone Number Webhook URL via API.
"""
import os
import sys
from twilio.rest import Client
from dotenv import load_dotenv

def update_webhook():
    load_dotenv()
    
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    phone_number = os.getenv("TWILIO_PHONE_NUMBER")
    base_url = os.getenv("BASE_URL")
    
    if not all([sid, token, phone_number, base_url]):
        print("Error: Missing required environment variables.")
        sys.exit(1)
        
    webhook_url = f"{base_url}/webhook/answer"
    
    print(f"Connecting to Twilio...")
    client = Client(sid, token)
    
    try:
        # Find the incoming phone number resource
        numbers = client.incoming_phone_numbers.list(phone_number=phone_number)
        
        if not numbers:
            print(f"Error: Could not find phone number {phone_number} in your Twilio account.")
            sys.exit(1)
            
        number_sid = numbers[0].sid
        print(f"Found number {phone_number} (SID: {number_sid})")
        
        # Update the webhook
        print(f"Updating Voice Webhook to: {webhook_url}")
        client.incoming_phone_numbers(number_sid).update(
            voice_url=webhook_url,
            voice_method="POST"
        )
        
        print("\n✅ Twilio Webhook Updated Successfully!")
        print(f"New Voice URL: {webhook_url}")
        
    except Exception as e:
        print(f"❌ Error updating Twilio: {e}")
        sys.exit(1)

if __name__ == "__main__":
    update_webhook()
