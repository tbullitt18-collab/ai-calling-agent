# Rain Check v2.0 API Documentation

## Base URL
`http://localhost:5000`

## Endpoints

### 1. Health & Status
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET    | `/`      | Service metadata and health status. |
| GET    | `/health`| Simple uptime check. |

### 2. Voice Cloning (NEW)
Manage your "Voice Twins" using ElevenLabs Professional Voice Cloning.

#### List Voices
- **GET** `/voices/`
- **Response**: List of voice objects containing `voice_id`, `name`, and labels.

#### Create Voice Clone
- **POST** `/voices/clone`
- **Content-Type**: `multipart/form-data`
- **Body**:
  - `name`: String (Name of the voice twin)
  - `files`: File[] (1 to 10 audio samples, 16kHz+, Mono WAV/MP3 preferred)
- **Response**:
  ```json
  {
      "status": "success",
      "voice_id": "eleven_voice_id",
      "profile_id": "mongo_profile_id",
      "message": "Cloning process initiated and profile created."
  }
  ```

#### Delete Voice
- **DELETE** `/voices/{voice_id}`
- **Response**: `{"success": true}`

### 3. Call Scheduling (NEW)
Automate your workplace calls at specific times.

#### Schedule Outbound Call
- **POST** `/session/schedule`
- **Body**:
  ```json
  {
      "to_number": "+1234567890",
      "time": "HH:MM" (24h format, e.g., "06:00")
  }
  ```
- **Response**:
  ```json
  {
      "status": "scheduled",
      "job_id": "call_identifier",
      "message": "Call scheduled for HH:MM"
  }
  ```

### 4. Telephony Webhooks (Twilio)
*Internal use only, configured in Twilio Console.*

- **POST** `/webhook/answer`: Unified answer webhook for incoming/outbound TwiML.
- **WSS**  `/ws/audio/{call_sid}`: Bidirectional ElevenLabs <-> Twilio audio stream.
