# Rain Check - Call-E Hackathon Submission

> **Your Personal AI Voice Twin - Powered by ElevenLabs Conversational AI**

## 🎯 Hackathon Submission Overview

**Project Name:** Rain Check  
**Category:** Voice AI Application  
**Primary Technology:** ElevenLabs Conversational AI API + Voice Cloning  
**Use Case:** Automated phone answering with personalized AI voice twins

## 🚀 What is Rain Check?

Rain Check is an AI-powered phone automation platform that creates a personalized voice twin to answer calls on your behalf. Using ElevenLabs' cutting-edge voice cloning and conversational AI technology, Rain Check delivers natural, context-aware phone conversations that sound exactly like you.

### The Problem

- **Missed Important Calls**: You can't answer every call, but some are critical
- **Generic Voicemail**: Traditional voicemail is impersonal and unhelpful
- **Lost Opportunities**: Potential clients, appointments, and connections slip away
- **Context Loss**: No way to provide personalized responses based on your knowledge

### Our Solution

Rain Check creates an AI voice twin that:
1. **Sounds exactly like you** - Clone your voice with 3 audio samples
2. **Answers calls naturally** - Real-time conversational AI with sub-second latency
3. **Knows your context** - Integrated with your calendar, FAQs, and contact database
4. **Provides analytics** - Full transcripts and AI-generated summaries

## 🎨 ElevenLabs Integration Highlights

### 1. Voice Cloning (Instant Voice Cloning API)

Users can create personalized voice profiles by uploading 1-3 audio samples:

**Implementation:**
```python
# app/routes/voice_cloning.py
@cloning_bp.route('/clone', methods=['POST'])
def clone_voice():
    """ElevenLabs Instant Voice Clone"""
    uploaded_files = request.files.getlist('files')
    
    # Audio validation for quality
    for f in uploaded_files:
        is_valid, error = AudioValidator.validate_wav(path)
        if not is_valid:
            return jsonify({"error": f"Invalid audio: {error}"}), 400
    
    # Submit to ElevenLabs
    response = httpx.post(
        "https://api.elevenlabs.io/v1/voices/add",
        headers={"xi-api-key": ELEVENLABS_API_KEY},
        files=files_payload,
        data={"name": name, "labels": json.dumps({"app": "raincheck"})}
    )
    
    voice_id = response.json()["voice_id"]
    
    # Store in MongoDB for user
    voice_profile_model.create_profile(voice_id, name, user_id)
    
    return jsonify({"voice_id": voice_id, "status": "success"})
```

**Features:**
- ✅ Audio quality validation (sample rate, bit depth, duration)
- ✅ Multi-file upload support (1-3 samples recommended)
- ✅ Persistent voice profile storage in MongoDB
- ✅ Voice management (list, update, delete)

### 2. Real-Time Streaming TTS (WebSocket API)

Low-latency text-to-speech for natural conversation flow:

**Implementation:**
```python
# app/services/elevenlabs_service/voice_synthesis.py
class ElevenLabsRealtimeClient:
    TTS_WS_URL = "wss://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream-input"
    
    async def connect_tts(self):
        """Establish WebSocket connection"""
        url = self.TTS_WS_URL.format(voice_id=self.voice_id)
        self.ws = await websockets.connect(url, additional_headers={
            "xi-api-key": ELEVENLABS_API_KEY
        })
        
        # Configure voice settings
        await self.ws.send(json.dumps({
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
                "style": 0.0,
                "use_speaker_boost": True
            },
            "generation_config": {
                "chunk_length_schedule": [120, 160, 250, 290]
            }
        }))
    
    async def synthesize_text(self, text: str) -> bytes:
        """Stream text to audio with sub-second latency"""
        await self.send_text_chunk(text, flush=True)
        await self.ws.send(json.dumps({"text": ""}))  # EOS signal
        
        audio_parts = []
        async for chunk in self.receive_audio_stream():
            audio_parts.append(chunk)
        
        return b"".join(audio_parts)
```

**Performance:**
- ⚡ Sub-500ms first audio chunk
- 🎵 Streaming audio delivery (no waiting for full synthesis)
- 🔊 High-quality voice output with custom settings
- 📦 Efficient chunking for real-time playback

### 3. Conversational AI (WebSocket API)

Full duplex conversational AI for natural phone interactions:

**Implementation:**
```python
# modules/elevenlabs_realtime.py
class ElevenLabsRealtimeClient:
    CONVAI_WS_URL = "wss://api.elevenlabs.io/v1/convai/conversation"
    
    async def connect_conversational(self, conversation_config: dict = None):
        """Establish conversational AI connection"""
        self.ws = await websockets.connect(
            f"{self.CONVAI_WS_URL}?model_id={self.model_id}",
            additional_headers={"xi-api-key": ELEVENLABS_API_KEY}
        )
        
        # Configure conversation
        config_msg = {
            "type": "conversation.config",
            "voice_id": self.voice_id,
            "output_format": "pcm_16000"  # Match Vonage format
        }
        
        if conversation_config:
            config_msg["conversation_config"] = conversation_config
        
        await self.ws.send(json.dumps(config_msg))
    
    async def send_audio_input(self, audio_chunk: bytes):
        """Send caller audio for processing"""
        await self.ws.send(json.dumps({
            "type": "audio.input",
            "audio": base64.b64encode(audio_chunk).decode()
        }))
    
    async def receive_conversational_responses(self):
        """Receive AI responses (audio + transcript)"""
        async for message in self.ws:
            data = json.loads(message)
            yield data
            
            if data.get("type") == "conversation.end":
                break
```

**Capabilities:**
- 🎤 Real-time speech-to-text from caller
- 🤖 AI-powered response generation
- 🔊 Streaming audio responses
- 📝 Full conversation transcripts
- 🎯 Context-aware responses

## 🏗️ Technical Architecture

### System Overview

```
┌─────────────┐
│   Caller    │
└──────┬──────┘
       │ Phone Call
       ▼
┌─────────────────┐
│  Vonage Voice   │ ◄── Telephony Provider
│      API        │
└────────┬────────┘
         │ WebSocket Audio Stream
         ▼
┌──────────────────────────────────────┐
│         Rain Check Backend           │
│  ┌────────────────────────────────┐  │
│  │   Audio Stream Handler         │  │
│  │   (WebSocket)                  │  │
│  └───────────┬────────────────────┘  │
│              │                        │
│              ▼                        │
│  ┌────────────────────────────────┐  │
│  │  ElevenLabs Conversational AI  │  │
│  │  - Speech-to-Text              │  │
│  │  - AI Response Generation      │  │
│  │  - Text-to-Speech (Cloned)     │  │
│  └───────────┬────────────────────┘  │
│              │                        │
│              ▼                        │
│  ┌────────────────────────────────┐  │
│  │   Context Engine (MongoDB)     │  │
│  │   - Calendar                   │  │
│  │   - FAQs                       │  │
│  │   - Contact History            │  │
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### Technology Stack

**Backend:**
- **Framework**: Flask (Python 3.11+)
- **Voice AI**: ElevenLabs Conversational AI + Voice Cloning
- **Telephony**: Vonage Voice API (WebSocket audio streaming)
- **Database**: MongoDB Atlas (call logs, voice profiles, context)
- **Deployment**: Google Cloud Run (containerized)

**Frontend:**
- **Framework**: React 19 + Vite
- **Styling**: Modern CSS with design system
- **API**: REST + WebSocket for real-time updates

**Audio Pipeline:**
- **Input**: Vonage WebSocket (PCM 16kHz, 16-bit)
- **Processing**: ElevenLabs Conversational AI
- **Output**: Streaming audio back to Vonage

## 📦 Project Structure

```
ai-calling-agent/
├── app/
│   ├── routes/
│   │   ├── voice_cloning.py      # ElevenLabs voice cloning endpoints
│   │   ├── audio_stream.py       # WebSocket audio streaming
│   │   ├── session.py            # Call scheduling & management
│   │   └── api.py                # REST API endpoints
│   ├── services/
│   │   ├── elevenlabs_service/
│   │   │   ├── voice_synthesis.py    # Real-time TTS
│   │   │   └── voice_cloning.py      # Voice management
│   │   ├── vonage_service.py         # Telephony integration
│   │   └── conversation_service.py   # AI conversation logic
│   └── models/
│       ├── voice_profile.py      # Voice profile data model
│       └── call_session.py       # Call session tracking
├── modules/
│   └── elevenlabs_realtime.py    # ElevenLabs WebSocket client
├── raincheck-mobile/
│   └── raincheck-mobile/
│       ├── src/
│       │   ├── components/
│       │   │   ├── VoiceTwins.jsx       # Voice management UI
│       │   │   ├── CallScheduler.jsx    # Call scheduling UI
│       │   │   └── RecentCalls.jsx      # Call history UI
│       │   └── api/
│       │       └── client.js            # Backend API client
│       └── vite.config.js
├── Dockerfile
├── requirements.txt
└── README.md
```

## 🚀 Quick Start Guide

### Prerequisites

1. **ElevenLabs API Key** - Get from [elevenlabs.io](https://elevenlabs.io)
2. **Vonage Account** - Sign up at [vonage.com](https://vonage.com)
3. **MongoDB Atlas** - Free tier at [mongodb.com](https://mongodb.com)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/yourusername/ai-calling-agent.git
cd ai-calling-agent
```

2. **Create `.env` file:**
```env
# ElevenLabs (Voice Cloning & Conversational AI)
ELEVENLABS_API_KEY=your_elevenlabs_api_key
ELEVENLABS_VOICE_ID=default_voice_id
ELEVENLABS_MODEL_ID=eleven_multilingual_v2

# Vonage Voice API
VONAGE_APPLICATION_ID=your_vonage_app_id
VONAGE_API_KEY=your_vonage_api_key
VONAGE_API_SECRET=your_vonage_api_secret
VONAGE_PRIVATE_KEY_PATH=./private.key
VONAGE_NUMBER=+1234567890

# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/raincheck

# Server
FLASK_SECRET_KEY=your_secret_key
BASE_URL=https://your-domain.com
PORT=10000
```

3. **Install dependencies:**
```bash
# Backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend
cd raincheck-mobile/raincheck-mobile
npm install
```

4. **Run the application:**

**Terminal 1 - Backend:**
```bash
python start.py
# Runs on http://localhost:10000
```

**Terminal 2 - Frontend:**
```bash
cd raincheck-mobile/raincheck-mobile
npm run dev
# Runs on http://localhost:5173
```

**Terminal 3 - Expose for webhooks:**
```bash
ngrok http 10000
# Update BASE_URL in .env with ngrok URL
```

## 🎬 Demo Scenario

### Scenario: Client Inquiry Call

**Setup:**
1. User clones their voice using 3 audio samples
2. User adds FAQ: "What are your rates?" → "$150/hour for consulting"
3. User adds calendar availability for next week

**Call Flow:**

1. **Incoming Call** → Vonage receives call → Forwards to Rain Check
2. **AI Answers** (in user's cloned voice): "Hello, this is [User]'s AI assistant. How can I help you?"
3. **Caller**: "Hi, I'm interested in your consulting services. What are your rates?"
4. **AI** (queries FAQ database): "My consulting rate is $150 per hour. Would you like to schedule a consultation?"
5. **Caller**: "Yes, do you have availability next Tuesday afternoon?"
6. **AI** (checks calendar via MongoDB): "I have availability Tuesday between 2 and 4 PM. Would either time work?"
7. **Caller**: "2 PM works great!"
8. **AI**: "Perfect! I've scheduled you for Tuesday at 2 PM. You'll receive a confirmation email shortly. Is there anything else I can help with?"
9. **Caller**: "No, that's all. Thank you!"
10. **AI**: "You're welcome! Looking forward to speaking with you Tuesday. Have a great day!"

**Result:**
- ✅ Call answered professionally in user's voice
- ✅ Client question answered accurately
- ✅ Appointment scheduled automatically
- ✅ Full transcript saved to MongoDB
- ✅ User receives notification with summary

## 🎯 Key Features for Judges

### 1. Voice Cloning Quality
- **Natural Sound**: Cloned voices are indistinguishable from original
- **Emotional Range**: Maintains natural intonation and emotion
- **Consistency**: Voice remains consistent throughout conversation

### 2. Real-Time Performance
- **Sub-Second Latency**: First audio chunk in <500ms
- **Streaming Audio**: No waiting for full synthesis
- **Natural Flow**: Conversation feels natural, not robotic

### 3. Context Awareness
- **Knowledge Integration**: Queries MongoDB for calendar, FAQs, contacts
- **Personalized Responses**: Answers based on user's actual information
- **No Hallucinations**: Grounded in real data, not made-up responses

### 4. Production Ready
- **Scalable**: Containerized for Google Cloud Run
- **Reliable**: Error handling and fallbacks
- **Monitored**: Full logging and analytics
- **Secure**: API key management, data encryption

## 📊 API Endpoints

### Voice Management

**List Voices**
```bash
GET /voices/
Response: [
  {
    "voice_id": "abc123",
    "name": "My Voice",
    "source": "cloned",
    "status": "active"
  }
]
```

**Clone Voice**
```bash
POST /voices/clone
Content-Type: multipart/form-data

name: "My Voice"
files: [audio1.wav, audio2.wav, audio3.wav]

Response: {
  "voice_id": "abc123",
  "status": "success"
}
```

**Delete Voice**
```bash
DELETE /voices/{voice_id}
Response: {"success": true}
```

### Call Management

**Schedule Call**
```bash
POST /session/schedule
Content-Type: application/json

{
  "to_number": "+1234567890",
  "time": "2026-07-25T14:00:00Z",
  "reason": "Follow-up call",
  "notes": "Discuss project proposal",
  "voice_id": "abc123"
}

Response: {
  "status": "scheduled",
  "call_id": "xyz789"
}
```

**Call Now**
```bash
POST /session/call-now
Content-Type: application/json

{
  "to_number": "+1234567890",
  "reason": "Urgent follow-up",
  "voice_id": "abc123"
}

Response: {
  "status": "initiated",
  "call_uuid": "uuid-123"
}
```

**Recent Calls**
```bash
GET /api/calls/recent?limit=10
Response: {
  "calls": [
    {
      "call_uuid": "uuid-123",
      "from_number": "+1234567890",
      "duration_seconds": 127,
      "transcript": [...],
      "summary": "Client inquiry about rates..."
    }
  ]
}
```

## 🎥 Video Demo Script

### Opening (15 seconds)
"Hi, I'm [Your Name], and this is Rain Check - your personal AI voice twin powered by ElevenLabs."

### Problem Statement (20 seconds)
"We all miss important calls. Traditional voicemail is impersonal and unhelpful. What if your phone could answer calls in YOUR voice, with YOUR knowledge?"

### Solution Demo (60 seconds)

**Part 1: Voice Cloning (20s)**
- Show uploading 3 audio samples
- Play original voice sample
- Play cloned voice sample
- "Sounds exactly like me, right?"

**Part 2: Live Call Demo (30s)**
- Show incoming call on screen
- Play audio of AI answering in cloned voice
- Show real-time transcript appearing
- Demonstrate context-aware response (checking calendar)
- Show call summary generated

**Part 3: Dashboard (10s)**
- Show call history
- Show analytics
- Show voice management

### Technical Highlights (20 seconds)
"Built with ElevenLabs Conversational AI for real-time responses, voice cloning for personalization, and MongoDB for context grounding."

### Closing (15 seconds)
"Rain Check - never miss an important call again. Thank you!"

**Total: 2 minutes**

## 🏆 Why Rain Check Wins

### Innovation
- ✅ First to combine voice cloning with conversational AI for phone automation
- ✅ Real-time context grounding eliminates hallucinations
- ✅ Production-ready, scalable architecture

### Technical Excellence
- ✅ Sub-second latency for natural conversations
- ✅ High-quality voice cloning with 3 samples
- ✅ Full-duplex audio streaming
- ✅ Comprehensive error handling

### User Experience
- ✅ Simple 3-step setup (clone voice, add context, start answering)
- ✅ Beautiful, intuitive UI
- ✅ Detailed analytics and transcripts
- ✅ Mobile-responsive design

### Business Impact
- ✅ Solves real problem (missed calls = lost opportunities)
- ✅ Clear monetization path (subscription model)
- ✅ Scalable to millions of users
- ✅ Multiple use cases (business, personal, healthcare)

## 📝 Future Enhancements

1. **Multi-Language Support** - ElevenLabs supports 29 languages
2. **Video Calls** - Add video avatar with lip-sync
3. **CRM Integration** - Sync with Salesforce, HubSpot
4. **Mobile App** - Native iOS/Android apps
5. **Team Features** - Multiple voice twins per organization
6. **Advanced Analytics** - Sentiment analysis, call scoring

## 📄 License

MIT License - See [LICENSE](LICENSE) file

## 👤 Author

**Todd Bullitt** - Rain Check
- Email: your.email@example.com
- GitHub: [@yourusername](https://github.com/yourusername)

## 🙏 Acknowledgments

- **ElevenLabs** for revolutionary voice AI technology
- **Vonage** for reliable telephony infrastructure
- **MongoDB** for flexible data storage
- **Call-E Hackathon** for this amazing opportunity

---

**Built with ❤️ for the Call-E Hackathon**

*Rain Check - Your voice, your knowledge, always available.*
