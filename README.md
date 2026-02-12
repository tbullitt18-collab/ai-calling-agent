# Rain Check - AI Voice Application

> **Multimodal AI voice application that simulates natural, two-way phone conversations between humans and a lifelike AI voice.**

Rain Check is a production-ready voice automation platform that makes AI sound human. It answers calls automatically, listens, understands context, and responds in real-time with sub-second latency.

## Features

- **Natural Conversations** - AI voice that feels confident, warm, and emotionally intelligent
- **Real-Time Latency** - <1 second end-to-end response time
- **Context Memory** - Maintains conversation context throughout the call
- **Intent Detection** - Automatically detects caller intent and asks clarifying follow-ups
- **Voice Cloning** - Use ElevenLabs to create custom voice personas
- **Call Analytics** - Full transcript logging with AI-generated summaries
- **Webhook API** - Easy integration with Vonage Voice API

## Architecture

```
┌─────────────┐    ┌──────────────────┐    ┌─────────────────────┐
│   Caller    │───▶│   Twilio Voice   │───▶│    Flask Backend    │
│  (Phone)    │◀───│  Voice Webhooks  │◀───│   /webhook/answer   │
└─────────────┘    └──────────────────┘    │   /webhook/event    │
                                           └──────────┬──────────┘
                         ┌────────────────────────────┼────────────────────────────┐
                         ▼                            ▼                            ▼
                ┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
                │   ElevenLabs    │         │     Claude      │         │    Redis        │
                │  Real-Time TTS  │         │   AI Intelligence  │         │  Session Store  │
                └─────────────────┘         └─────────────────┘         └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- Twilio account with Voice capabilities
- ElevenLabs API key
- Claude (Anthropic) API key
- Redis (for session management)
- MongoDB (for call logging)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ai-calling-agent.git
   cd ai-calling-agent
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   # source venv/bin/activate  # Linux/Mac
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment:**
   ```bash
   copy .env.example .env
   # Edit .env with your API keys
   ```

5. **Run the application:**
   ```bash
   python app.py
   ```

### Twilio Deployment Setup

1. **Start Ngrok** (to expose your local server):
   ```bash
   ngrok http 5000
   ```
2. Copy the **Forwarding URL** (e.g., `https://1234.ngrok-free.app`).
3. Go to **Twilio Console** > **Phone Numbers** > **Manage** > **Active Numbers**.
4. Click your phone number.
5. Under **Voice & Fax** > **A Call Comes In**:
   - Select **Webhook**
   - URL: `YOUR_NGROK_URL/webhook/answer` (e.g., `https://1234.ngrok-free.app/webhook/answer`)
   - HTTP Method: `POST`
6. Save configuration.

### Docker Deployment

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f raincheck

# Stop services
docker-compose down
```

## Configuration

Create a `.env` file with the following variables:

```env
# Twilio Voice API
TWILIO_ACCOUNT_SID=your_account_sid
TWILIO_AUTH_TOKEN=your_auth_token
TWILIO_PHONE_NUMBER=your_twilio_number

# Claude (Anthropic)
CLAUDE_API_KEY=your_claude_key

# ElevenLabs Real-Time API
ELEVENLABS_API_KEY=your_api_key
ELEVENLABS_VOICE_ID=your_voice_id
ELEVENLABS_MODEL_ID=eleven_turbo_v2_5

# Database
MONGODB_URI=mongodb://localhost:27017/raincheck
REDIS_URL=redis://localhost:6379

# Server
FLASK_ENV=development
BASE_URL=https://your-domain.ngrok.io
```

## API Endpoints

### Webhooks (Twilio)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/webhook/answer` | POST | Handles incoming call (returns TwiML) |
| `/webhook/outbound-twiml` | POST | Handles outbound call connection |

### REST API

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/api/call/initiate` | POST | Start outbound call |
| `/api/call/<uuid>` | GET | Get call details |
| `/api/calls/recent` | GET | List recent calls |
| `/api/analytics` | GET | Get call analytics |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `/ws/audio/<call_sid>` | Real-time audio streaming (Media Stream) |

## Project Structure

```
/ai-calling-agent
├── app.py                 # Main Flask application
├── config.py              # Configuration loader
├── requirements.txt       # Python dependencies
├── Dockerfile            # Container build
├── docker-compose.yml    # Service orchestration
├── /modules
│   ├── twilio_api.py          # Twilio TwiML & Call handling
│   ├── elevenlabs_realtime.py # ElevenLabs WebSocket client
│   ├── session_manager.py     # Redis session handling
│   ├── conversation_engine.py # Claude-based AI response
│   ├── intent_detector.py     # Claude-based intent logic
│   └── call_logger.py         # MongoDB logging
└── /tests
    ├── test_webhooks.py       # Endpoint tests
    ├── test_modules.py        # Unit tests
```

## Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=modules --cov-report=html

# Run specific test file
pytest tests/test_webhooks.py -v
```

## Customizing the AI Persona

Edit the `AgentPersona` configuration in your code:

```python
from modules.conversation_engine import ConversationEngine, AgentPersona

persona = AgentPersona(
    name="Your Agent Name",
    warmth=0.8,       # 0-1: How warm/caring
    confidence=0.7,   # 0-1: How assertive
    empathy=0.9,      # 0-1: How understanding
    tone="friendly",  # professional, friendly, casual, formal
    custom_instructions="Additional behavior rules..."
)

engine = ConversationEngine(persona=persona)
```

## Performance Tuning

### Latency Targets

| Component | Target | Actual |
|-----------|--------|--------|
| Twilio → Flask | <50ms | - |
| STT Processing | <200ms | - |
| Claude Response | <400ms | - |
| TTS Generation | <250ms | - |

### Optimization Tips

1. **Use ElevenLabs Turbo** - `eleven_turbo_v2_5` for lowest latency
2. **Stream responses** - Don't buffer full audio
3. **Regional deployment** - Deploy close to Twilio edge

## License

MIT License - see [LICENSE](LICENSE) for details.

## Author

Built with ❤️ by Rain Check Team
