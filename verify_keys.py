"""
Verify API keys for Twilio, Claude, and ElevenLabs.
"""
import os
import requests
import anthropic
from twilio.rest import Client
from dotenv import load_dotenv

def verify_twilio():
    print("\nTesting Twilio...")
    sid = os.getenv("TWILIO_ACCOUNT_SID")
    token = os.getenv("TWILIO_AUTH_TOKEN")
    try:
        client = Client(sid, token)
        account = client.api.v2010.accounts(sid).fetch()
        print(f"Twilio Active: {account.friendly_name} ({account.status})")
        return True
    except Exception as e:
        print(f"Twilio Failed: {e}")
        return False

def verify_claude():
    print("\nTesting Claude (Anthropic)...")
    key = os.getenv("CLAUDE_API_KEY")
    try:
        client = anthropic.Anthropic(api_key=key)
        resp = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1,
            messages=[{"role": "user", "content": "Hi"}]
        )
        print("Claude Active")
        return True
    except Exception as e:
        print(f"Claude Failed: {e}")
        return False

def verify_elevenlabs():
    print("\nTesting ElevenLabs...")
    key = os.getenv("ELEVENLABS_API_KEY")
    try:
        resp = requests.get(
            "https://api.elevenlabs.io/v1/user",
            headers={"xi-api-key": key}
        )
        if resp.status_code == 200:
            user = resp.json()
            sub = user.get('subscription', {})
            print(f"ElevenLabs Active: {sub.get('tier')} tier ({sub.get('character_count')}/{sub.get('character_limit')} chars used)")
            return True
        else:
            print(f"ElevenLabs Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"ElevenLabs Connection Error: {e}")
        return False

def verify_vonage():
    print("\nTesting Vonage...")
    key = os.getenv("VONAGE_API_KEY")
    secret = os.getenv("VONAGE_API_SECRET")
    private_key_path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key")
    
    if not key or not secret:
        print("Vonage Failed: Missing API Key or Secret")
        return False
        
    # 1. Verify API Key/Secret via Balance endpoint
    try:
        resp = requests.get(
            "https://rest.nexmo.com/account/get-balance",
            params={"api_key": key, "api_secret": secret},
            timeout=10
        )
        if resp.status_code == 200:
            data = resp.json()
            print(f"Vonage API: Active (Balance: {data.get('value'):.2f} EUR)")
        else:
            print(f"Vonage API Failed: {resp.status_code} - {resp.text}")
            return False
    except Exception as e:
        print(f"Vonage Connection Error: {e}")
        return False

    # 2. Verify Private Key exists
    if os.path.exists(private_key_path):
        print(f"Vonage Key: Found at {private_key_path}")
    else:
        print(f"Vonage Key: Missing at {private_key_path}")
        return False
        
    return True

if __name__ == "__main__":
    load_dotenv()
    print("API KEY VERIFICATION")
    print("====================")
    
    t = verify_twilio()
    c = verify_claude()
    e = verify_elevenlabs()
    v = verify_vonage()
    
    if t and c and e and v:
        print("\nALL SYSTEMS GO!")
    else:
        print("\nSOME KEYS FAILED. CHECK .ENV")
