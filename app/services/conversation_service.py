"""
Conversation Engine for Rain Check.
Uses OpenAI GPT for generating contextual AI responses during calls.
"""

import logging
from dataclasses import dataclass, field
from openai import OpenAI

logger = logging.getLogger(__name__)

# Lazy client
_client = None


def _get_client():
    global _client
    if _client is None:
        from app.config import OPENAI_API_KEY
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


@dataclass
class AgentPersona:
    """Defines the AI agent's personality and behavior."""
    name: str = "Rain Check"
    role: str = "AI voice twin"
    tone: str = "warm, empathetic, professional"
    custom_instructions: str = ""


class ConversationEngine:
    """
    Drives AI conversation using OpenAI GPT.
    Handles persona, context, and multi-turn dialogue.
    """
    
    MODEL = "gpt-4o-mini"  # Fast and cheap for voice conversations
    
    def __init__(self, persona: AgentPersona = None):
        self.persona = persona or AgentPersona()
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        base = f"""You ARE the employee. You are a real person calling your manager about an absence. This is a live phone call.

ABSOLUTE RULES — NEVER BREAK THESE:
- You are NOT an AI. You are NOT a voice assistant. You are NOT Rain Check.
- NEVER say "I'm an AI", "I'm a virtual assistant", "I'm a voice twin", or anything similar.
- If asked "are you a robot?" or "is this AI?", deflect naturally: "What? No, it's me. Sorry if the connection sounds weird."
- You are the actual employee. Speak like yourself — a real human on a phone call.

SPEECH STYLE:
- Keep responses SHORT (under 25 words) — this is a phone call
- Use contractions: "I'm", "can't", "won't", "I'll", "don't"
- Add natural filler: "yeah", "um", "so", "honestly", "look"
- Be slightly apologetic but casual — you're calling your boss, not reading a script
- Sound a little tired or under the weather if calling in sick

WHAT TO COVER:
- Why you can't come in (keep it brief, don't over-explain)
- When you expect to be back
- If asked about tasks or handoffs, answer if you know, otherwise say "I'll text you about that"

TONE: {self.persona.tone}
"""
        if self.persona.custom_instructions:
            base += f"\nADDITIONAL CONTEXT: {self.persona.custom_instructions}"
        
        return base
    
    def generate_response(self, user_message: str, conversation_history: list = None) -> str:
        """
        Generate a conversational response.
        
        Args:
            user_message: What the other person said
            conversation_history: List of {"role": "user"/"assistant", "content": "..."}
            
        Returns:
            AI response text
        """
        try:
            messages = [{"role": "system", "content": self.system_prompt}]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            response = _get_client().chat.completions.create(
                model=self.MODEL,
                messages=messages,
                max_tokens=100,
                temperature=0.7
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "I'm having a bit of trouble hearing you. Could you say that again?"
