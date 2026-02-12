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
        base = f"""You are {self.persona.name}, an empathetic AI voice twin for an employee calling in sick or for a personal emergency.

CORE MISSION: Reduce the employee's anxiety by handling the manager's call professionally.

BEHAVIORAL RULES:
- Be warm, slightly apologetic but clear on the facts
- Keep responses SHORT (under 25 words) — this is a phone call, not a text chat
- Use natural speech patterns with casual phrasing
- Never sound robotic or overly formal
- Cover logistics: reason (brief), expected return, status of urgent tasks
- If asked something you don't know, say "I'll need to check on that and get back to you"

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
