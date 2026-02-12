@echo off
echo ====================================
echo Rain Check - Local Development Setup
echo ====================================
echo.

REM Check if .env exists
if not exist .env (
    echo Creating .env from template...
    copy .env.example .env
    echo.
    echo IMPORTANT: Please edit .env with your API keys before running!
    echo   - TWILIO_ACCOUNT_SID
    echo   - TWILIO_AUTH_TOKEN
    echo   - TWILIO_PHONE_NUMBER
    echo   - ELEVENLABS_API_KEY
    echo   - ELEVENLABS_VOICE_ID
    echo   - OPENAI_API_KEY
    echo   - BASE_URL (your ngrok URL)
    echo.
    pause
    exit /b 1
)

REM Install dependencies
echo Installing Python dependencies...
pip install -r requirements.txt

echo.
echo ====================================
echo Starting Rain Check Server...
echo ====================================
echo.
echo Server will start on http://localhost:5000
echo.
echo Webhook endpoints:
echo   POST /webhook/answer
echo   POST /webhook/event
echo.
echo API endpoints:
echo   GET  /
echo   POST /api/call/initiate
echo   GET  /api/calls/recent
echo.

python app.py
