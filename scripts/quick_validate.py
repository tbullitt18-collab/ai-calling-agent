#!/usr/bin/env python3
"""Quick API connectivity check."""
import os, sys
sys.path.insert(0, '.')
from dotenv import load_dotenv
load_dotenv()
import requests

print("=== VONAGE ===")
key = os.getenv("VONAGE_API_KEY", "")
secret = os.getenv("VONAGE_API_SECRET", "")
try:
    r = requests.get("https://api.nexmo.com/v2/applications", auth=(key, secret), timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        apps = r.json().get("_embedded", {}).get("applications", [])
        print(f"  Apps: {len(apps)}")
        for a in apps:
            print(f"    - {a.get('name')}: {a.get('id')}")
    else:
        print(f"  Body: {r.text[:150]}")
except Exception as e:
    print(f"  Error: {e}")

print("=== VONAGE NUMBER ===")
num = os.getenv("VONAGE_NUMBER", "")
print(f"  Configured: {num}")

print("=== PRIVATE KEY ===")
pk_path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key")
exists = os.path.exists(pk_path)
print(f"  File exists: {exists} ({pk_path})")

print("=== ELEVENLABS ===")
elkey = os.getenv("ELEVENLABS_API_KEY", "")
try:
    r = requests.get("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": elkey}, timeout=10)
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        voices = r.json().get("voices", [])
        cloned = [v for v in voices if v.get("category") != "premade"]
        print(f"  Total voices: {len(voices)}, Cloned: {len(cloned)}")
except Exception as e:
    print(f"  Error: {e}")

print("=== ELEVENLABS TTS PCM ===")
vid = os.getenv("ELEVENLABS_VOICE_ID", "")
try:
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{vid}",
        headers={"xi-api-key": elkey, "Content-Type": "application/json", "Accept": "audio/pcm"},
        params={"output_format": "pcm_16000"},
        json={"text": "Test.", "model_id": "eleven_multilingual_v2",
              "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}},
        timeout=15
    )
    print(f"  Status: {r.status_code}")
    if r.status_code == 200:
        size = len(r.content)
        dur = (size / (16000 * 2)) * 1000
        print(f"  PCM output: {size} bytes (~{dur:.0f}ms)")
except Exception as e:
    print(f"  Error: {e}")

print("=== OPENAI ===")
oaikey = os.getenv("OPENAI_API_KEY", "")
try:
    from openai import OpenAI
    c = OpenAI(api_key=oaikey)
    r = c.chat.completions.create(model="gpt-4o-mini", messages=[{"role":"user","content":"say OK"}], max_tokens=5)
    print(f"  Response: {r.choices[0].message.content.strip()}")
except Exception as e:
    print(f"  Error: {e}")

print("=== DEEPGRAM ===")
dgkey = os.getenv("DEEPGRAM_API_KEY", "")
if dgkey:
    try:
        r = requests.get("https://api.deepgram.com/v1/projects",
                         headers={"Authorization": f"Token {dgkey}"}, timeout=10)
        print(f"  Status: {r.status_code}")
    except Exception as e:
        print(f"  Error: {e}")
else:
    print("  NOT CONFIGURED - add DEEPGRAM_API_KEY to .env")

print("=== APP WIRING ===")
try:
    from app import create_app
    app = create_app()
    with app.test_client() as tc:
        r = tc.get("/health")
        data = r.get_json()
        print(f"  Health: {data}")
        r2 = tc.get("/webhook/answer?uuid=val-001")
        ncco = r2.get_json()
        actions = [a.get("action") for a in ncco]
        print(f"  NCCO actions: {actions}")
        ws_uri = ncco[1]["endpoint"][0]["uri"]
        print(f"  WebSocket URI: {ws_uri}")
except Exception as e:
    print(f"  Error: {e}")

print("=== DONE ===")
