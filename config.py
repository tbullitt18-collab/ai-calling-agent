"""
Rain Check - Configuration Module
Loads and validates environment variables for the AI voice application.
"""

import os
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


# Twilio Configuration
TWILIO_ACCOUNT_SID = _require_env("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = _require_env("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = _require_env("TWILIO_PHONE_NUMBER")

# ElevenLabs Configuration
ELEVENLABS_API_KEY = _require_env("ELEVENLABS_API_KEY")
ELEVENLABS_VOICE_ID = _require_env("ELEVENLABS_VOICE_ID")
ELEVENLABS_MODEL_ID = _get_env("ELEVENLABS_MODEL_ID", "eleven_turbo_v2_5")

# Claude (Anthropic) Configuration
CLAUDE_API_KEY = _require_env("CLAUDE_API_KEY")

# Database Configuration
MONGODB_URI = _require_env("MONGODB_URI")
REDIS_URL = _get_env("REDIS_URL", "redis://localhost:6379")

# Server Configuration
BASE_URL = _require_env("BASE_URL")
FLASK_ENV = _get_env("FLASK_ENV", "development")
