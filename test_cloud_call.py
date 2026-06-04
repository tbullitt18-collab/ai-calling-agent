"""
Test call via Vonage API — calls the Cloud Run deployment webhooks.
The Vonage answer webhook is now pointed at Cloud Run, so this will
exercise the full production pipeline.
"""
import os, jwt, time, uuid, requests
from dotenv import load_dotenv
load_dotenv()

app_id = os.getenv("VONAGE_APPLICATION_ID")
vonage_number = os.getenv("VONAGE_NUMBER", "").lstrip("+")
base_url = os.getenv("BASE_URL")

with open(os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key"), "r") as f:
    private_key = f.read()

# Generate JWT
payload = {
    "application_id": app_id,
    "iat": int(time.time()),
    "jti": str(uuid.uuid4()),
    "exp": int(time.time()) + 3600
}
token = jwt.encode(payload, private_key, algorithm="RS256")

to_number = "2058812202"
voice_id = "EkR0b2fNU4kBZ6syl9Vn" # Todd Raincheck voice ID (from ElevenLabs config)
answer_url = f"{base_url}/webhook/answer?reason=Sick+Day&voice_id={voice_id}"
event_url = f"{base_url}/webhook/events"

print(f"Calling {to_number} from {vonage_number}")
print(f"Answer URL: {answer_url}")
print(f"Event URL:  {event_url}")

resp = requests.post(
    "https://api.nexmo.com/v1/calls",
    headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    },
    json={
        "to": [{"type": "phone", "number": to_number}],
        "from": {"type": "phone", "number": vonage_number},
        "answer_url": [answer_url],
        "event_url": [event_url]
    },
    timeout=15
)

print(f"\nStatus: {resp.status_code}")
print(f"Response: {resp.text[:500]}")
