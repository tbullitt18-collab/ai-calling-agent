"""
Rain Check Call Simulation Script
Tests the full conversation + TTS pipeline locally without making real calls.
Mocks Vonage to verify: Gemini conversation → Google Cloud TTS → audio output.
"""

import os
import sys
import json
import time
from unittest.mock import MagicMock, patch
from dotenv import load_dotenv

load_dotenv()


def run_simulation():
    print("🌧️  RAIN CHECK — CALL FLOW SIMULATION (GOOGLE CLOUD NATIVE)")
    print("=" * 60)
    print("Testing: Vonage NCCO ➔ Vertex AI Gemini ➔ Google Cloud TTS (Studio Voice)")
    print()
    
    # ── Step 1: Test NCCO Generation ─────────────────────────────────
    print("[Step 1] Testing NCCO Generation...")
    try:
        from app.services.vonage_service import generate_answer_ncco, generate_error_ncco
        
        ncco = generate_answer_ncco(
            call_uuid="sim-call-001",
            reason="sick_day",
            voice_id="en-US-Studio-O"
        )
        print(f"  ✅ NCCO generated: {len(ncco)} actions")
        for i, action in enumerate(ncco):
            print(f"     Action {i+1}: {action['action']}")
            if action['action'] == 'talk':
                print(f"       Text: \"{action['text']}\"")
            elif action['action'] == 'connect':
                ep = action['endpoint'][0]
                print(f"       Type: {ep['type']}")
                print(f"       URI: {ep['uri']}")
                print(f"       Format: {ep['content-type']}")
        
        error_ncco = generate_error_ncco()
        print(f"  ✅ Error NCCO generated: {error_ncco[0]['text']}")
    except Exception as e:
        print(f"  ❌ NCCO generation failed: {e}")
        return
    
    # ── Step 2: Test Session Management ──────────────────────────────
    print(f"\n[Step 2] Testing Session Management...")
    try:
        from app.models.call_session import SessionManager
        
        sm = SessionManager()
        session = sm.create_session("sim-call-001", "+15550001234")
        print(f"  ✅ Session created: {session.call_uuid}")
        
        context = {"reason": "sick_day", "notes": "Fever since last night", "voice_id": "en-US-Studio-O"}
        sm.set_context("sim-call-001", context)
        retrieved = sm.get_context("sim-call-001")
        print(f"  ✅ Context stored and retrieved: {retrieved.get('reason')}")
        
        sm.add_turn("sim-call-001", "assistant", "Hi, calling about a schedule update.")
        sm.add_turn("sim-call-001", "user", "Oh okay, what's going on?")
        history = sm.get_conversation_history("sim-call-001")
        print(f"  ✅ Conversation history: {len(history)} turns")
    except Exception as e:
        print(f"  ❌ Session management failed: {e}")
    
    # ── Step 3: Test Conversation Engine (Gemini) ────────────────────
    print(f"\n[Step 3] Testing Conversation Engine (Gemini)...")
    try:
        from app.services.conversation_service import ConversationEngine, AgentPersona
        
        persona = AgentPersona(
            custom_instructions="You are calling to report: sick_day. Additional context: Fever since last night."
        )
        engine = ConversationEngine(persona=persona)
        print(f"  ✅ ConversationEngine initialized with persona: {persona.name}")
        print(f"  System prompt preview: \"{engine.system_prompt[:100]}...\"")
        
        # Simulate conversation turns
        conversation = []
        
        manager_says = "Hello, this is Sarah. Who's calling?"
        print(f"\n  👤 Manager: \"{manager_says}\"")
        conversation.append({"role": "user", "content": manager_says})
        
        response1 = engine.generate_response(manager_says, conversation)
        print(f"  🤖 AI: \"{response1}\"")
        conversation.append({"role": "assistant", "content": response1})
        
        manager_says2 = "Oh no, I hope you feel better. Do you think you'll be back tomorrow?"
        print(f"\n  👤 Manager: \"{manager_says2}\"")
        conversation.append({"role": "user", "content": manager_says2})
        
        response2 = engine.generate_response(manager_says2, conversation)
        print(f"  🤖 AI: \"{response2}\"")
        conversation.append({"role": "assistant", "content": response2})
        
        manager_says3 = "Okay, take care of yourself. I'll make sure your meetings are covered."
        print(f"\n  👤 Manager: \"{manager_says3}\"")
        conversation.append({"role": "user", "content": manager_says3})
        
        response3 = engine.generate_response(manager_says3, conversation)
        print(f"  🤖 AI: \"{response3}\"")
        
        print(f"\n  ✅ Full conversation: {len(conversation) + 1} turns completed")
        
    except Exception as e:
        print(f"  ❌ Conversation engine failed: {e}")
    
    # ── Step 4: Test Google Cloud TTS ────────────────────────────────
    print(f"\n[Step 4] Testing Google Cloud TTS...")
    try:
        from app.services.google_ai_service import synthesize_speech
        
        test_text = "Hi, I won't be able to make it in today."
        print(f"  Synthesizing text: \"{test_text}\" using voice en-US-Studio-O")
        
        audio = synthesize_speech(test_text, voice_name="en-US-Studio-O")
        if audio:
            print(f"  ✅ Synthesized {len(audio)} bytes of audio (raw PCM)")
            
            # Save test audio as raw PCM
            with open("test_output.pcm", "wb") as f:
                f.write(audio)
            print(f"  ✅ Audio saved to test_output.pcm")
        else:
            print("  ❌ TTS returned empty/None audio content.")
            
    except Exception as e:
        print(f"  ❌ Google Cloud TTS failed: {e}")
    
    # ── Summary ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("🌧_ SIMULATION COMPLETE")
    print()
    print("Pipeline: Phone ↔ Vonage (NCCO) ↔ Flask ↔ Vertex AI Gemini ↔ Google Cloud TTS")
    print()
    print("Next steps:")
    print("  1. Authenticate local gcloud: gcloud auth application-default login")
    print("  2. Start local server: python start.py")
    print("  3. Initiate a live test call: python test_live_call.py")


if __name__ == "__main__":
    run_simulation()
