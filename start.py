#!/usr/bin/env python3
"""
Render startup script.
Tests imports and app creation before handing off to gunicorn.
"""
import os
import sys
import traceback

# Force UTF-8
os.environ['PYTHONIOENCODING'] = 'utf-8'

def test_startup():
    """Test that the app can be created successfully."""
    print("=" * 60)
    print("STARTUP DIAGNOSTIC")
    print("=" * 60)
    print(f"Python: {sys.version}")
    print(f"CWD: {os.getcwd()}")
    print(f"PORT: {os.environ.get('PORT', 'NOT SET')}")
    print(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'NOT SET')}")
    
    # Test critical imports
    tests = [
        ("flask", "from flask import Flask"),
        ("gunicorn", "import gunicorn"),
        ("openai", "from openai import OpenAI"),
        ("vonage", "import vonage"),
        ("app.config", "from app.config import FLASK_ENV"),
        ("app.create_app", "from app import create_app; app = create_app()"),
    ]
    
    for name, code in tests:
        try:
            exec(code)
            print(f"  OK: {name}")
        except Exception as e:
            print(f"  FAIL: {name}")
            print(f"        {type(e).__name__}: {e}")
            traceback.print_exc()
            return False
    
    print("=" * 60)
    print("ALL CHECKS PASSED")
    print("=" * 60)
    return True

if __name__ == "__main__":
    if not test_startup():
        print("STARTUP FAILED - see errors above")
        sys.exit(1)
    
    # Start gunicorn
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
