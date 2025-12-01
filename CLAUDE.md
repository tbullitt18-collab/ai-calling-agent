# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Rain Check** is an AI-powered calling agent that makes automated phone calls on behalf of users. It uses voice cloning, natural language processing, and phone APIs to handle scenarios like calling in sick to work, requesting time off, or other workplace communications.

## Architecture

### Backend (Python/Flask)
- **app.py**: Main Flask application (~537 lines)
  - JWT-based authentication with bcrypt password hashing
  - RESTful API endpoints for users, voice profiles, managers, schedules, and calls
  - Vonage Voice API integration for phone calls with NCCO webhooks
  - ElevenLabs for voice synthesis and cloning
  - Claude AI (Anthropic) for natural conversation generation
  - MongoDB for user data, call history, and conversation logs

### Frontend (React Native/Expo)
- **app/**: Expo Router-based mobile application
  - `index.tsx`: Home/dashboard
  - `call.tsx`: Initiate calls
  - `clone-voice.tsx`: Voice profile management
  - `contacts.tsx`: Manager contact management
  - `history.tsx`: Call history view
  - `script-generator.tsx`: AI script generation
  - `voices.tsx`: Voice library
  - `settings.tsx`: User settings
  - `analytics.tsx`: Usage analytics
  - `lib/supabase.ts`: Supabase client configuration

### Core Modules (`modules/`)
- **agent_tools.py**: Tool definitions for AI agent
- **api_auth.py**: API authentication helpers
- **caller.py**: Call orchestration logic
- **chatbot.py**: Conversation management
- **mongodb.py**: Database connection utilities
- **tts.py**: Text-to-speech wrappers
- **twilio_api.py**: Legacy Twilio integration

### MCP Server
- **mcp_server.py**: FastMCP server exposing calling functionality via Model Context Protocol

## Development Commands

### Backend Setup
```bash
# Install Python dependencies
pip install -r requirements.txt

# Configure environment variables (copy from .env.example)
cp .env.example .env
# Edit .env with your credentials

# Run Flask development server (port 5000)
python app.py

# Run with ngrok for webhook testing
ngrok http 5000
# Update NGROK_URL in .env with the ngrok URL
```

### Frontend Setup
```bash
# Install Node dependencies
npm install

# Start Expo development server
npm start

# Run on specific platforms
npm run android    # Android emulator/device
npm run ios        # iOS simulator (macOS only)
npm run web        # Web browser
```

### MCP Server
```bash
# Run MCP server (port 8000)
python mcp_server.py
```

### Testing
```bash
# Test ElevenLabs integration
python test_eleven.py

# Test Vosk speech recognition
python test_vosk.py
```

## Key Implementation Details

### Call Flow Architecture
1. **User initiates call** → `POST /api/calls/initiate`
2. **Backend creates Vonage call** → Vonage dials manager's phone
3. **Manager answers** → Vonage hits `GET/POST /api/calls/answer` webhook
4. **ElevenLabs generates greeting audio** → Streams to call via NCCO
5. **Manager speaks** → Vonage transcribes speech, sends to `/api/calls/speech`
6. **Claude generates response** → Based on conversation history and context
7. **ElevenLabs converts response to audio** → Streams to call
8. **Loop continues** until conversation ends
9. **Call events logged** → `POST /api/calls/event` webhook

### Voice Profile System
- Users upload voice samples to ElevenLabs
- Voice profiles stored in user document with `elevenlabs_voice_id`
- Only one voice profile can be active per user
- Active voice used for all outbound calls

### Authentication Flow
- Registration: `POST /api/auth/register` → JWT token returned
- Login: `POST /api/auth/login` → JWT token returned
- Protected routes use `@token_required` decorator
- JWT tokens expire after 7 days

### Database Schema (MongoDB)
**users collection**:
- Authentication: `email`, `password` (bcrypt hashed), `username`
- Profile: `first_name`, `last_name`, `created_at`
- Voice: `voice_profiles[]` (name, elevenlabs_voice_id, is_active)
- Contacts: `manager_contacts[]` (name, phone, email, is_primary)
- Schedule: `work_schedule{}` (day → time mappings, timezone)
- Calls: `scheduled_calls[]`, `call_history[]`, `monthly_call_count`
- Conversation: `conversation_history[]` (maintained during active calls)

### NCCO Webhook Pattern
Vonage uses NCCO (Nexmo Call Control Objects) JSON format:
```json
[
  {
    "action": "stream",
    "streamUrl": ["https://your-domain/audio/file.mp3"],
    "bargeIn": false
  },
  {
    "action": "input",
    "type": ["speech"],
    "speech": {
      "maxSpeechTime": 60,
      "timeout": 10,
      "language": "en-US"
    },
    "eventUrl": ["https://your-domain/api/calls/speech"]
  }
]
```

### Environment Variables
Required secrets (see `.env.example`):
- **Vonage**: `VONAGE_APPLICATION_ID`, `VONAGE_PHONE_NUMBER`, `VONAGE_PRIVATE_KEY_PATH`
- **ElevenLabs**: `ELEVENLABS_API_KEY`
- **Claude**: `CLAUDE_API_KEY`
- **MongoDB**: `MONGODB_URI`
- **Flask**: `FLASK_SECRET_KEY`, `FLASK_ENV`
- **Ngrok**: `NGROK_URL` (for local webhook testing)

## Deployment

### Render.com (render.yaml)
Two services configured:
1. **Flask API** (`ai-calling-agent-flask`): Main backend on port 5000
2. **MCP Server** (`ai-calling-agent-mcp`): MCP endpoint on port 8000

### Mobile App
Build Expo app for production:
```bash
npm run build  # Exports web bundle
```

For native apps, configure EAS Build in Expo.

## Important Notes

- **Audio files saved to `static/audio/`**: Generated on-the-fly during calls with timestamp filenames
- **Private key handling**: Vonage requires RSA private key file (`.pem` format), path specified in env
- **Ngrok required for local development**: Vonage webhooks need public HTTPS URLs
- **Conversation history cleared**: Currently cleared per call, not persisted long-term
- **Monthly call limits**: Tracked in `monthly_call_count` field (no enforcement logic yet)
- **Legacy Twilio code**: `twilio_api.py` and references in `.env.example` are legacy, Vonage is now used

## Common Development Tasks

### Adding a new API endpoint
1. Add route handler in `app.py` with appropriate decorators (`@token_required` if auth needed)
2. Update frontend service in `services/api.ts` to call new endpoint
3. Add error handling and logging

### Integrating a new voice provider
1. Create new module in `modules/` (e.g., `new_tts.py`)
2. Implement text-to-speech function matching signature in `tts.py`
3. Update `answer_call()` and `speech_webhook()` in `app.py` to support new provider
4. Add environment variables to `.env.example` and config.py

### Debugging call flow
1. Check ngrok URL is active and matches `NGROK_URL` in `.env`
2. Monitor Flask logs for webhook hits
3. Check Vonage Dashboard → Logs for call events
4. Verify audio files being created in `static/audio/`
5. Test ElevenLabs connectivity with `test_eleven.py`
