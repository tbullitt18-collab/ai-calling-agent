from dotenv import load_dotenv
load_dotenv()

def test_booking_and_sms():
    from app.services.anthropic_service import claude_chat
    from app.services.mongodb_mcp_service import MongoDBMCPService
    from app.services.vonage_service import _get_voice

    class FakeVonageService:
        def send_sms(self, to_number, text):
            print(f"Fake sending SMS to {to_number}: {text}")
            return "SMS sent successfully."

    services = {
        "mongo": MongoDBMCPService(),
        "vonage": FakeVonageService()
    }

    system_prompt = (
        "You are an AI receptionist. CALLER_PHONE: 14045550000. "
        "Today is 2026-07-23. The user_id for this business is 'demo_user_001'."
    )

    messages = [
        {"role": "user", "content": "Book a meeting for tomorrow at 3 PM called 'Strategy Session' and text me the confirmation."}
    ]

    result = claude_chat(system_prompt, messages, services=services, use_tools=True)
    print("Final response:", result["text"])
    assert "booked" in result["text"].lower() or "strategy session" in result["text"].lower(), \
        "Expected booking confirmation in response"
    print("✅ Booking + SMS test passed")

if __name__ == "__main__":
    test_booking_and_sms()
