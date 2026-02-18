#!/usr/bin/env python3
"""
Render startup script with step-by-step import diagnostics.
Tests each import individually to pinpoint exactly what crashes.
If all imports pass, starts gunicorn. If any fail, starts a minimal
error-reporting server so Render stays 'live' and we can see the error.
"""
import os
import sys
import traceback
import json

os.environ['PYTHONIOENCODING'] = 'utf-8'

errors = []

def test_import(name, code):
    """Test a single import and record result."""
    try:
        exec(code, {})
        print(f"  [OK] {name}", flush=True)
        return True
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  [FAIL] {name}: {msg}", flush=True)
        traceback.print_exc()
        errors.append({"step": name, "error": msg})
        return False

def run_diagnostics():
    print("=" * 60, flush=True)
    print("RAIN CHECK - STARTUP DIAGNOSTICS", flush=True)
    print(f"Python {sys.version}", flush=True)
    print(f"CWD: {os.getcwd()}", flush=True)
    print(f"PORT: {os.environ.get('PORT', 'NOT SET')}", flush=True)
    print("=" * 60, flush=True)
    
    steps = [
        ("flask", "import flask"),
        ("flask_cors", "import flask_cors"),
        ("flask_sock", "import flask_sock"),
        ("openai", "import openai"),
        ("vonage", "import vonage"),
        ("pymongo", "import pymongo"),
        ("redis", "import redis"),
        ("schedule", "import schedule"),
        ("websockets", "import websockets"),
        ("httpx", "import httpx"),
        ("gunicorn", "import gunicorn"),
        ("jwt", "import jwt"),
        ("app.config", "from app.config import FLASK_ENV"),
        ("app.models.call_session", "from app.models.call_session import SessionManager"),
        ("app.models.voice_profile", "from app.models.voice_profile import VoiceProfile"),
        ("app.services.vonage_service", "from app.services.vonage_service import generate_answer_ncco"),
        ("app.services.conversation_service", "from app.services.conversation_service import ConversationEngine"),
        ("app.services.elevenlabs_service", "from app.services.elevenlabs_service.voice_synthesis import ElevenLabsRealtimeClient"),
        ("app.services.elevenlabs_service.voice_cloning", "from app.services.elevenlabs_service.voice_cloning import VoiceCloningService"),
        ("app.services.scheduler_service", "from app.services.scheduler_service import CallScheduler"),
        ("app.services.call_logger_service", "from app.services.call_logger_service import get_call_logger"),
        ("app.__init__", "from app import create_app"),
        ("create_app()", "from app import create_app; app = create_app()"),
        ("wsgi module", "import wsgi; app = wsgi.app"),
    ]
    
    all_ok = True
    for name, code in steps:
        if not test_import(name, code):
            all_ok = False
            # Continue testing to find ALL failures
    
    print("=" * 60, flush=True)
    if all_ok:
        print("ALL CHECKS PASSED", flush=True)
    else:
        print(f"FAILED: {len(errors)} step(s)", flush=True)
        for e in errors:
            print(f"  - {e['step']}: {e['error']}", flush=True)
    print("=" * 60, flush=True)
    
    return all_ok

def start_error_server():
    """Start a minimal server that reports the error on every request."""
    from http.server import HTTPServer, BaseHTTPRequestHandler
    
    class ErrorHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(503)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                "status": "startup_failed",
                "errors": errors
            }).encode())
        def log_message(self, format, *args):
            pass
    
    port = int(os.environ.get("PORT", 10000))
    print(f"Starting error-reporting server on port {port}", flush=True)
    HTTPServer(("0.0.0.0", port), ErrorHandler).serve_forever()

if __name__ == "__main__":
    if run_diagnostics():
        # All good - start gunicorn
        port = os.environ.get("PORT", "10000")
        os.execvp("gunicorn", [
            "gunicorn", "wsgi:app",
            "--bind", f"0.0.0.0:{port}",
            "--workers", "1",
            "--timeout", "120",
            "--access-logfile", "-",
            "--error-logfile", "-",
            "--log-level", "info"
        ])
    else:
        # Start error server so Render stays "live" and we can see errors
        start_error_server()
