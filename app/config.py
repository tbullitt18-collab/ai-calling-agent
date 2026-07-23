"""
Rain Check - Configuration Module
Loads and validates environment variables for the AI voice application.
Supports both local development (file-based private key) and
production (env var private key content).
"""

import os
import tempfile
from dotenv import load_dotenv

load_dotenv()


def _require_env(key: str) -> str:
    """Require an environment variable to be set."""
    value = os.getenv(key)
    if not value:
        raise ValueError(f"Required environment variable {key} is not set")
    return value


def _get_env(key: str, default: str = None) -> str:
    """Get an environment variable with optional default."""
    return os.getenv(key, default)


def _resolve_private_key() -> str:
    """
    Resolve Vonage private key - supports both:
    - File path (local dev): VONAGE_PRIVATE_KEY_PATH=./private.key
    - Inline content (Render): VONAGE_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----...
    
    Returns path to a readable private key file.
    """
    # Check for inline key content first (production/Render)
    key_b64 = os.getenv("VONAGE_PRIVATE_KEY_BASE64")
    if key_b64:
        import base64
        key_content = base64.b64decode(key_b64).decode('utf-8')
    else:
        key_content = os.getenv("VONAGE_PRIVATE_KEY")
        
    if key_content:
        # Write to a temp file since Vonage SDK expects a file path
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.key', delete=False)
        # Handle escaped newlines from env vars
        key_content = key_content.replace("\\n", "\n")
        tmp.write(key_content)
        tmp.close()
        return tmp.name
    
    # Fall back to file path (local development)
    key_path = os.getenv("VONAGE_PRIVATE_KEY_PATH", "./private.key")
    if os.path.exists(key_path):
        return key_path
    
    raise ValueError(
        "Vonage private key not found. Set VONAGE_PRIVATE_KEY (content) "
        "or VONAGE_PRIVATE_KEY_PATH (file path)."
    )


# Vonage Configuration
VONAGE_API_KEY = _require_env("VONAGE_API_KEY")
VONAGE_API_SECRET = _require_env("VONAGE_API_SECRET")
VONAGE_APPLICATION_ID = _get_env("VONAGE_APPLICATION_ID", "bed9794a-0f5b-4e51-a32c-3b751f5f292a")
VONAGE_PRIVATE_KEY_PATH = _resolve_private_key()
VONAGE_NUMBER = _require_env("VONAGE_NUMBER")

# ElevenLabs Configuration (Voice Cloning & Synthesis & ConvAI)
ELEVENLABS_API_KEY = _get_env('ELEVENLABS_API_KEY')
ELEVENLABS_VOICE_ID = _get_env('ELEVENLABS_VOICE_ID')
ELEVENLABS_MODEL_ID = _get_env('ELEVENLABS_MODEL_ID', 'eleven_multilingual_v2')
ELEVENLABS_AGENT_ID = _get_env('ELEVENLABS_AGENT_ID')  # ConvAI agent ID from ElevenLabs dashboard

# Google Cloud / Vertex AI Configuration
GOOGLE_CLOUD_PROJECT = _require_env("GOOGLE_CLOUD_PROJECT")
GOOGLE_CLOUD_LOCATION = _get_env("GOOGLE_CLOUD_LOCATION", "us-central1")
# GOOGLE_APPLICATION_CREDENTIALS is read automatically by Google client libraries

# OpenAI Configuration (legacy — optional, only used if Gemini fallback needed)
OPENAI_API_KEY = _get_env("OPENAI_API_KEY")

# Deepgram Configuration (legacy — optional, replaced by Google Cloud STT)
DEEPGRAM_API_KEY = _get_env("DEEPGRAM_API_KEY")

# Database Configuration
MONGODB_URI = _get_env("MONGODB_URI", "mongodb://localhost:27017")
REDIS_URL = _get_env("REDIS_URL", "redis://localhost:6379")

# Server Configuration
BASE_URL = _require_env("BASE_URL")
FLASK_ENV = _get_env("FLASK_ENV", "development")
FLASK_HOST = _get_env("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(_get_env("FLASK_PORT", "5000"))
SCHEDULER_SECRET = _get_env("SCHEDULER_SECRET", "raincheck-default-scheduler-secret")
