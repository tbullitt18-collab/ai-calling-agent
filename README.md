# Rain Check - Your Grounded AI Voice Twin

> **An AI voice application that simulates natural, two-way phone conversations, deeply integrated with your personal knowledge base via MongoDB and powered by Google Gemini.**

**Rain Check** is a production-ready voice automation platform built for the **Google Cloud Rapid Agent Hackathon 2026 (MongoDB Track)**. It answers calls automatically, listens, understands context, and responds in real-time. What sets Rain Check apart is its use of the **MongoDB Model Context Protocol (MCP)**—it doesn't just sound like you, it *knows* what you know.

During a call, the Gemini-powered agent dynamically queries your MongoDB Atlas database to answer scheduling questions, retrieve FAQs, and pull up contact context, completely eliminating hallucinations.

## 🚀 Features

- **Gemini Intelligence** - Powered by Google's state-of-the-art **Gemini 1.5 Flash** for blazing fast, highly contextual reasoning.
- **MongoDB MCP Integration** - Real-time context grounding using a MongoDB Model Context Protocol server. The AI queries your live schedule and FAQs during the call.
- **Voice Cloning** - Users can clone their own voice using ElevenLabs for a truly personalized AI Twin.
- **Natural Conversations** - Sub-second latency, detecting caller intent and asking clarifying follow-ups.
- **Call Analytics** - Full transcripts and AI-generated summaries saved securely in MongoDB.
- **Google Cloud Native** - Containerized and deployed on Google Cloud Run for infinite scalability.

## 🏗️ Architecture & Technology Stack

- **Core AI / LLM:** Google Cloud Vertex AI (Gemini 1.5 Flash)
- **Knowledge Base:** MongoDB Atlas & MongoDB MCP
- **Telephony:** Vonage Voice API
- **Voice Generation / TTS:** ElevenLabs API
- **Hosting:** Google Cloud Run (Containerized Flask App)

## 🏁 Quick Start (Local Development)

### Prerequisites
- Python 3.11+
- Google Cloud Project with Vertex AI enabled
- Vonage Voice API credentials
- ElevenLabs API key
- MongoDB Atlas cluster

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/yourusername/ai-calling-agent.git
   cd ai-calling-agent
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure your environment:**
   Create a `.env` file in the root directory and populate it with your credentials:
   ```env
   # Google Cloud
   GOOGLE_CLOUD_PROJECT=your-project-id
   GOOGLE_CLOUD_LOCATION=us-central1

   # Vonage Voice API
   VONAGE_APPLICATION_ID=your-app-id
   VONAGE_API_KEY=your-api-key
   VONAGE_API_SECRET=your-api-secret
   VONAGE_PRIVATE_KEY_PATH=./private.key
   VONAGE_NUMBER=your-vonage-number

   # Database (MongoDB MCP)
   MONGODB_URI=mongodb+srv://...

   # ElevenLabs
   ELEVENLABS_API_KEY=your-elevenlabs-key
   ELEVENLABS_VOICE_ID=your-voice-id
   ELEVENLABS_MODEL_ID=eleven_multilingual_v2

   # Server Config
   FLASK_SECRET_KEY=your-secret
   BASE_URL=https://your-ngrok-or-cloudrun-url
   ```

5. **Run the application:**
   ```bash
   python start.py
   ```

## ☁️ Google Cloud Run Deployment

Rain Check is designed to be easily deployed on Google Cloud Run.

1. **Build and submit the Docker image:**
   ```bash
   gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/raincheck-api
   ```

2. **Deploy to Cloud Run:**
   ```bash
   gcloud run deploy raincheck-api \
     --image gcr.io/YOUR_PROJECT_ID/raincheck-api \
     --platform managed \
     --region us-central1 \
     --allow-unauthenticated
   ```

3. **Set Environment Variables:**
   Ensure you pass all required environment variables via the Cloud Run console or CLI.

## 🤝 The Hackathon Implementation

For the **Google Cloud Rapid Agent Hackathon**, we specifically built:
1. **Google AI Integration**: Replaced legacy LLM architectures with `google-genai`, utilizing Gemini 1.5 Flash's massive context window and speed for real-time voice synthesis.
2. **MongoDB MCP Track**: Implemented a dynamic MongoDB MCP service that exposes database functions (`search_calendar`, `query_faq`, `lookup_contact`) directly to the Gemini model via Function Calling.

## 📜 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👤 Author

Built with ❤️ by Todd Brown (Rain Check)
