# Rain Check - Your Personal AI Voice Twin

> **Powered by ElevenLabs Conversational AI - Natural phone conversations in your own voice**

**Rain Check** is a production-ready voice automation platform that creates a personalized AI voice twin to answer phone calls on your behalf. Using ElevenLabs' cutting-edge voice cloning and conversational AI technology, Rain Check delivers natural, context-aware phone conversations that sound exactly like you.

## 🎯 Call-E Hackathon Submission

This project is submitted for the **Call-E Hackathon**, showcasing the power of ElevenLabs' voice AI technology for real-world phone automation.

**📄 [View Full Hackathon Submission Details](CALL_E_HACKATHON.md)**

## 🚀 Key Features

- **🎤 Voice Cloning** - Clone your voice with just 3 audio samples using ElevenLabs Instant Voice Cloning
- **💬 Real-Time Conversations** - Sub-second latency conversational AI powered by ElevenLabs
- **🧠 Context-Aware** - Integrated with MongoDB for calendar, FAQs, and contact context
- **📊 Call Analytics** - Full transcripts and AI-generated summaries for every call
- **📱 Modern UI** - Beautiful React dashboard for managing voices and calls
- **☁️ Cloud-Ready** - Containerized and deployable to Google Cloud Run

## 🏗️ Technology Stack

- **Voice AI**: ElevenLabs Conversational AI + Voice Cloning API
- **Telephony**: Vonage Voice API (WebSocket audio streaming)
- **Backend**: Flask (Python 3.11+)
- **Database**: MongoDB Atlas
- **Frontend**: React 19 + Vite
- **Deployment**: Google Cloud Run (Docker)

## 🎬 How It Works

1. **Clone Your Voice** - Upload 1-3 audio samples to create your AI voice twin
2. **Add Context** - Configure your calendar, FAQs, and contact information
3. **Answer Calls** - Rain Check answers calls in your voice with your knowledge
4. **Review & Learn** - Get full transcripts and summaries of every conversation

## 🏁 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- ElevenLabs API key ([get one here](https://elevenlabs.io))
- Vonage Voice API credentials ([sign up here](https://vonage.com))
- MongoDB Atlas cluster ([free tier](https://mongodb.com))

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ai-calling-agent.git
   cd ai-calling-agent
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

   Required variables:
   ```env
   # ElevenLabs
   ELEVENLABS_API_KEY=your_api_key
   ELEVENLABS_VOICE_ID=default_voice_id
   ELEVENLABS_MODEL_ID=eleven_multilingual_v2

   # Vonage
   VONAGE_APPLICATION_ID=your_app_id
   VONAGE_API_KEY=your_api_key
   VONAGE_API_SECRET=your_api_secret
   VONAGE_PRIVATE_KEY_PATH=./private.key
   VONAGE_NUMBER=+1234567890

   # MongoDB
   MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/raincheck

   # Server
   FLASK_SECRET_KEY=your_secret_key
   BASE_URL=https://your-domain.com
   PORT=10000
   ```

3. **Install backend dependencies:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

4. **Install frontend dependencies:**
   ```bash
   cd raincheck-mobile/raincheck-mobile
   npm install
   cd ../..
   ```

5. **Run the application:**

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

   **Terminal 3 - Expose for webhooks (development):**
   ```bash
   ngrok http 10000
   # Update BASE_URL in .env with ngrok URL
   ```

6. **Access the dashboard:**
   Open http://localhost:5173 in your browser

## 📦 Project Structure

```
ai-calling-agent/
├── app/
│   ├── routes/
│   │   ├── voice_cloning.py      # ElevenLabs voice cloning
│   │   ├── audio_stream.py       # WebSocket audio streaming
│   │   ├── session.py            # Call management
│   │   └── api.py                # REST API
│   ├── services/
│   │   ├── elevenlabs_service/   # ElevenLabs integration
│   │   ├── vonage_service.py     # Telephony
│   │   └── conversation_service.py
│   └── models/
│       ├── voice_profile.py      # Voice data model
│       └── call_session.py       # Call tracking
├── raincheck-mobile/
│   └── raincheck-mobile/
│       ├── src/
│       │   ├── components/       # React UI components
│       │   └── api/              # API client
│       └── vite.config.js
├── Dockerfile
├── requirements.txt
├── CALL_E_HACKATHON.md          # Full hackathon details
└── README.md
```

## 🎯 API Endpoints

### Voice Management

```bash
# List all voices
GET /voices/

# Clone a new voice
POST /voices/clone
Content-Type: multipart/form-data
Body: name, files[]

# Delete a voice
DELETE /voices/{voice_id}
```

### Call Management

```bash
# Schedule a call
POST /session/schedule
Body: {
  "to_number": "+1234567890",
  "time": "2026-07-25T14:00:00Z",
  "reason": "Follow-up",
  "voice_id": "abc123"
}

# Make immediate call
POST /session/call-now
Body: {
  "to_number": "+1234567890",
  "reason": "Urgent",
  "voice_id": "abc123"
}

# Get recent calls
GET /api/calls/recent?limit=10
```

## ☁️ Deployment

### Google Cloud Run

1. **Build Docker image:**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/raincheck-api
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy raincheck-api \
     --image gcr.io/YOUR_PROJECT_ID/raincheck-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated \
     --set-env-vars ELEVENLABS_API_KEY=xxx,VONAGE_API_KEY=xxx
   ```

3. **Update Vonage webhooks:**
   Point your Vonage application webhooks to your Cloud Run URL

## 🎥 Demo Video

[Link to demo video showcasing voice cloning and live call handling]

## 🏆 Why Rain Check?

- **Natural Conversations**: ElevenLabs' conversational AI delivers human-like interactions
- **Your Voice**: Voice cloning makes it truly personal
- **Context-Aware**: Knows your schedule, FAQs, and contact history
- **Production-Ready**: Scalable, reliable, and secure
- **Beautiful UI**: Modern React dashboard for easy management

## 🔮 Future Enhancements

- Multi-language support (ElevenLabs supports 29 languages)
- Video calls with AI avatar
- CRM integrations (Salesforce, HubSpot)
- Mobile apps (iOS/Android)
- Team collaboration features
- Advanced analytics and sentiment analysis

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

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