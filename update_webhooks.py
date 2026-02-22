import os
import requests
import base64
from dotenv import load_dotenv

def update_webhooks():
    load_dotenv()
    
    api_key = os.getenv("VONAGE_API_KEY")
    api_secret = os.getenv("VONAGE_API_SECRET")
    app_id = os.getenv("VONAGE_APPLICATION_ID")
    base_url = os.getenv("BASE_URL")
    
    if not all([api_key, api_secret, app_id, base_url]):
        print("Error: Missing required environment variables.")
        return False
        
    print(f"Updating Vonage App {app_id}")
    print(f"New Base URL: {base_url}")
    
    # Construct Basic Auth header
    auth_str = f"{api_key}:{api_secret}"
    auth_b64 = base64.b64encode(auth_str.encode()).decode()
    headers = {
        "Authorization": f"Basic {auth_b64}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    # capability configuration
    answer_url = f"{base_url}/webhook/answer"
    event_url = f"{base_url}/webhook/events"
    
    payload = {
        "capabilities": {
            "voice": {
                "webhooks": {
                    "answer_url": {
                        "address": answer_url,
                        "http_method": "POST"
                    },
                    "event_url": {
                        "address": event_url,
                        "http_method": "POST"
                    }
                }
            }
        }
    }
    
    try:
        resp = requests.put(
            f"https://api.nexmo.com/v2/applications/{app_id}",
            headers=headers,
            json=payload,
            timeout=10
        )
        
        if resp.status_code == 200:
            data = resp.json()
            msg = "\nSUCCESS: Webhooks updated!"
            print(msg)
            print(f"App Name: {data.get('name')}")
            voice_caps = data.get('capabilities', {}).get('voice', {}).get('webhooks', {})
            print(f"Answer URL: {voice_caps.get('answer_url', {}).get('address')}")
            print(f"Event URL:  {voice_caps.get('event_url', {}).get('address')}")
            with open("webhook_result.txt", "w") as f:
                f.write(msg)
            return True
        else:
            msg = f"\nFAILED: {resp.status_code}\n{resp.text}"
            print(msg)
            with open("webhook_result.txt", "w") as f:
                f.write(msg)
            return False
            
    except Exception as e:
        print(f"\nERROR: {e}")
        return False

if __name__ == "__main__":
    update_webhooks()
