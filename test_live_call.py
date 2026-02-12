"""
Rain Check Real Call Tester
Initiates a real call using the configured Twilio credentials.
REQUIRES: Valid .env with Twilio API keys and ngrok URL.
"""

import os
import sys
import requests
from dotenv import load_dotenv

def test_live_call():
    load_dotenv()
    
    print("📞 RAIN CHECK - LIVE CALL TESTER (TWILIO)")
    print("=========================================")
    
    # Check config
    base_url = os.getenv("BASE_URL")
    if not base_url or "localhost" in base_url and "ngrok" not in base_url:
        print("⚠️ WARNING: BASE_URL seems to be localhost. Twilio cannot reach localhost.")
        print(f"   Current BASE_URL: {base_url}")
        
    # Get phone number
    to_number = input("\nEnter phone number to call (E.164 format, e.g. +12025551234): ")
    if not to_number:
        print("❌ Phone number required.")
        sys.exit(1)
        
    print(f"\nInitiating call to {to_number}...")
    
    try:
        # Use the local API endpoint which calls Twilio
        response = requests.post(
            "http://localhost:5000/api/call/initiate",
            json={"to": to_number}
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Call Initiated Successfully!")
            print(f"   Call SID: {data.get('call_uuid')}")
            print("\nCheck your phone! 📱")
        else:
            print(f"\n❌ Call Failed: {response.status_code}")
            print(f"   {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ Could not connect to local server.")
        print("   Make sure 'python app.py' is running.")

if __name__ == "__main__":
    test_live_call()
