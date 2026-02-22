#!/usr/bin/env python3
"""
API Connectivity Validation Script for Rain Check.
Tests each external service with live credentials.
"""

import os
import sys
import json

# Load .env
from dotenv import load_dotenv
load_dotenv()

results = {}

def check(name, fn):
    try:
        ok, detail = fn()
        results[name] = {"status": "PASS" if ok else "FAIL", "detail": detail}
        symbol = "PASS" if ok else "FAIL"
        print(f"  [{symbol}] {name}: {detail}", flush=True)
    except Exception as e:
        results[name] = {"status": "ERROR", "detail": str(e)}
        print(f"  [ERROR] {name}: {e}", flush=True)

# ── Vonage ────────────────────────────────────────────────────────────
def check_vonage():
    import requests
    key = os.getenv("VONAGE_API_KEY")
    secret = os.getenv("VONAGE_API_SECRET")
    if not key or not secret:
        return False, "VONAGE_API_KEY or VONAGE_API_SECRET not set"
    r = requests.get(
        "https://api.nexmo.com/v2/applications",
        auth=(key, secret),
        headers={"Accept": "application/json"},
        timeout=10
    )
    if r.status_code == 200:
        apps = r.json().get("_embedded", {}).get("applications", [])
        names = [a.get("name", "unnamed") for a in apps[:3]]
        return True, f"{len(apps)} application(s): {', '.join(names)}"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"

# ── Vonage Number ─────────────────────────────────────────────────────
def check_vonage_number():
    import requests
    key = os.getenv("VONAGE_API_KEY")
    secret = os.getenv("VONAGE_API_SECRET")
    number = os.getenv("VONAGE_NUMBER")
    if not number:
        return False, "VONAGE_NUMBER not set"
    r = requests.get(
        "https://rest.nexmo.com/account/numbers",
        params={"api_key": key, "api_secret": secret, "pattern": number},
        timeout=10
    )
    if r.status_code == 200:
        nums = r.json().get("numbers", [])
        if nums:
            n = nums[0]
            return True, f"Number {number} found (country: {n.get('country')}, type: {n.get('type')})"
        return False, f"Number {number} not found in account"
    return False, f"HTTP {r.status_code}"

# ── OpenAI ────────────────────────────────────────────────────────────
def check_openai():
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return False, "OPENAI_API_KEY not set"
    from openai import OpenAI
    client = OpenAI(api_key=key)
    r = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "respond with just the word OK"}],
        max_tokens=5
    )
    text = r.choices[0].message.content.strip()
    return True, f"gpt-4o-mini responded: '{text}'"

# ── ElevenLabs ────────────────────────────────────────────────────────
def check_elevenlabs():
    import requests
    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        return False, "ELEVENLABS_API_KEY not set"
    r = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers={"xi-api-key": key},
        timeout=10
    )
    if r.status_code == 200:
        voices = r.json().get("voices", [])
        cloned = [v for v in voices if v.get("category") != "premade"]
        return True, f"{len(voices)} voices ({len(cloned)} custom/cloned)"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"

# ── ElevenLabs TTS PCM Output ─────────────────────────────────────────
def check_elevenlabs_tts_pcm():
    import requests
    key = os.getenv("ELEVENLABS_API_KEY")
    voice_id = os.getenv("ELEVENLABS_VOICE_ID")
    if not key or not voice_id:
        return False, "ELEVENLABS_API_KEY or ELEVENLABS_VOICE_ID not set"
    r = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={
            "xi-api-key": key,
            "Content-Type": "application/json",
            "Accept": "audio/pcm",
        },
        params={"output_format": "pcm_16000"},
        json={
            "text": "Test.",
            "model_id": os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2"),
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=15
    )
    if r.status_code == 200:
        size = len(r.content)
        duration_ms = (size / (16000 * 2)) * 1000
        return True, f"PCM 16kHz output OK ({size} bytes, ~{duration_ms:.0f}ms audio)"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"

# ── Deepgram ──────────────────────────────────────────────────────────
def check_deepgram():
    import requests
    key = os.getenv("DEEPGRAM_API_KEY")
    if not key:
        return False, "DEEPGRAM_API_KEY not set — STT will not work"
    r = requests.get(
        "https://api.deepgram.com/v1/projects",
        headers={"Authorization": f"Token {key}"},
        timeout=10
    )
    if r.status_code == 200:
        projects = r.json().get("projects", [])
        return True, f"{len(projects)} project(s)"
    return False, f"HTTP {r.status_code}: {r.text[:100]}"

# ── Vonage Private Key ────────────────────────────────────────────────
def check_private_key():
    path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key")
    content = os.getenv("VONAGE_PRIVATE_KEY") or os.getenv("VONAGE_PRIVATE_KEY_BASE64")
    if content:
        return True, "Private key provided via environment variable"
    if os.path.exists(path):
        size = os.path.getsize(path)
        return True, f"Private key file found at {path} ({size} bytes)"
    return False, f"No private key: file {path} not found, env vars not set"

# ── App Import ────────────────────────────────────────────────────────
def check_app_import():
    from app import create_app
    app = create_app()
    client = app.test_client()
    r = client.get("/health")
    data = r.get_json()
    return True, f"Flask app OK — telephony: {data.get('telephony')}, env: {data.get('environment')}"

# ── Webhook Answer ────────────────────────────────────────────────────
def check_webhook_answer():
    from app import create_app
    app = create_app()
    client = app.test_client()
    r = client.get("/webhook/answer?uuid=validation-test-001&from=+15550000000")
    ncco = r.get_json()
    if not isinstance(ncco, list) or len(ncco) < 2:
        return False, f"Invalid NCCO: {ncco}"
    ws_uri = ncco[1].get("endpoint", [{}])[0].get("uri", "")
    return True, f"NCCO OK — talk + connect. WS: {ws_uri}"


# ── Run all ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60, flush=True)
    print("RAIN CHECK — API CONNECTIVITY VALIDATION", flush=True)
    print("=" * 60, flush=True)

    check("vonage_api", check_vonage)
    check("vonage_number", check_vonage_number)
    check("vonage_private_key", check_private_key)
    check("openai", check_openai)
    check("elevenlabs_api", check_elevenlabs)
    check("elevenlabs_tts_pcm", check_elevenlabs_tts_pcm)
    check("deepgram", check_deepgram)
    check("app_import", check_app_import)
    check("webhook_answer", check_webhook_answer)

    print("=" * 60, flush=True)
    passed = sum(1 for r in results.values() if r["status"] == "PASS")
    total = len(results)
    failed = [k for k, v in results.items() if v["status"] != "PASS"]
    print(f"RESULT: {passed}/{total} checks passed", flush=True)
    if failed:
        print(f"FAILED: {', '.join(failed)}", flush=True)
    print("=" * 60, flush=True)
