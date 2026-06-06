#!/usr/bin/env python3
"""
Bulletproof Render startup script.
Strategy: start error-reporting server in a thread FIRST, 
then test imports. If imports pass, replace the server with gunicorn.
"""
import os
import sys
import json
import threading
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler

PORT = int(os.environ.get("PORT", 10000))
status = {"phase": "starting", "errors": [], "checks": []}

class StatusHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200 if not status["errors"] else 503)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    def log_message(self, fmt, *args):
        pass

# Start HTTP server immediately in a thread
server = HTTPServer(("0.0.0.0", PORT), StatusHandler)
server_thread = threading.Thread(target=server.serve_forever, daemon=True)
server_thread.start()
print(f"Status server started on port {PORT}", flush=True)

# Handle Google Cloud credentials from env var (production)
gcred_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
if gcred_json and not os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
    import tempfile, base64
    try:
        cred_content = base64.b64decode(gcred_json).decode('utf-8')
    except Exception:
        cred_content = gcred_json  # Already plain JSON
    tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
    tmp.write(cred_content)
    tmp.close()
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = tmp.name
    print(f"Google Cloud credentials written to {tmp.name}", flush=True)

# Now test imports one by one
def check(name, code):
    try:
        exec(code, {"__name__": "__check__"})
        status["checks"].append({"name": name, "ok": True})
        print(f"  OK: {name}", flush=True)
        return True
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
        tb = traceback.format_exc()
        status["checks"].append({"name": name, "ok": False, "error": err})
        status["errors"].append({"step": name, "error": err, "traceback": tb})
        print(f"  FAIL: {name}: {err}", flush=True)
        print(tb, flush=True)
        return False

print("=" * 50, flush=True)
print(f"Python {sys.version}", flush=True)
print(f"CWD: {os.getcwd()}", flush=True)
print(f"Files: {os.listdir('.')}", flush=True)
print("=" * 50, flush=True)

all_ok = True
for name, code in [
    ("flask", "import flask"),
    ("flask_cors", "import flask_cors"),
    ("flask_sock", "import flask_sock"),
    ("vonage", "import vonage"),
    ("pymongo", "import pymongo"),
    ("redis_pkg", "import redis"),
    ("schedule", "import schedule"),
    ("websockets", "import websockets"),
    ("httpx", "import httpx"),
    ("gunicorn", "import gunicorn"),
    ("jwt", "import jwt"),
    ("google_genai", "import google.genai"),
    ("google_cloud_speech", "import google.cloud.speech_v2"),
    ("google_cloud_tts", "import google.cloud.texttospeech"),
    ("app.config", "from app import config"),
    ("app.models.call_session", "from app.models import call_session"),
    ("app.models.voice_profile", "from app.models import voice_profile"),
    ("app.services.vonage_service", "from app.services import vonage_service"),
    ("app.services.conversation_service", "from app.services import conversation_service"),
    ("app.services.scheduler_service", "from app.services import scheduler_service"),
    ("app.services.call_logger_service", "from app.services import call_logger_service"),
    ("app.routes.health", "from app.routes import health"),
    ("app.routes.auth", "from app.routes import auth"),
    ("app.routes.audio_stream", "from app.routes import audio_stream"),
    ("app.routes.voice_cloning_route", "from app.routes import voice_cloning"),
    ("app.routes.session", "from app.routes import session"),
    ("app.routes.api", "from app.routes import api"),
    ("app_init", "from app import create_app"),
    ("create_app", "from app import create_app; create_app()"),
]:
    if not check(name, code):
        all_ok = False

status["phase"] = "all_passed" if all_ok else "failed"
print(f"\nResult: {'ALL PASSED' if all_ok else 'FAILED'}", flush=True)

if all_ok:
    print("Stopping status server, starting gunicorn...", flush=True)
    server.shutdown()
    os.execvp("gunicorn", [
        "gunicorn", "wsgi:app",
        "--bind", f"0.0.0.0:{PORT}",
        "--workers", "1",
        "--threads", "4",
        "--worker-class", "gthread",
        "--timeout", "120",
        "--access-logfile", "-",
        "--error-logfile", "-",
    ])
else:
    print(f"Keeping error server alive on port {PORT}. Query / for details.", flush=True)
    status["phase"] = "error_server_running"
    server_thread.join()  # Keep main thread alive
