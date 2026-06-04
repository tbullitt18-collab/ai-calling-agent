"""Update Vonage webhooks to Cloud Run URL using JWT auth."""
import os, jwt, time, uuid, requests
from dotenv import load_dotenv
load_dotenv()

app_id = os.getenv("VONAGE_APPLICATION_ID")
base_url = os.getenv("BASE_URL")
key_path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key")

with open(key_path, "r") as f:
    private_key = f.read()

payload = {
    "application_id": app_id,
    "iat": int(time.time()),
    "jti": str(uuid.uuid4()),
    "exp": int(time.time()) + 3600
}
token = jwt.encode(payload, private_key, algorithm="RS256")

answer_url = f"{base_url}/webhook/answer"
event_url = f"{base_url}/webhook/events"

print(f"App ID: {app_id}")
print(f"Answer URL: {answer_url}")
print(f"Event URL:  {event_url}")

resp = requests.put(
    f"https://api.nexmo.com/v2/applications/{app_id}",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={
        "name": "Rain Check Production",
        "capabilities": {
            "voice": {
                "webhooks": {
                    "answer_url": {"address": answer_url, "http_method": "GET"},
                    "event_url": {"address": event_url, "http_method": "POST"}
                }
            }
        }
    },
    timeout=10
)

print(f"\nStatus: {resp.status_code}")
if resp.status_code == 200:
    data = resp.json()
    voice = data.get("capabilities", {}).get("voice", {}).get("webhooks", {})
    print(f"Answer: {voice.get('answer_url', {}).get('address')}")
    print(f"Events: {voice.get('event_url', {}).get('address')}")
    print("SUCCESS: Webhooks updated!")
else:
    print(resp.text[:500])
