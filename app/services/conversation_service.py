"""
Conversation Engine for Rain Check.
Uses Vertex AI Gemini for generating contextual AI responses during calls.
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentPersona:
    """Defines the AI agent's personality and behavior."""
    name: str = "Rain Check"
    role: str = "AI voice twin"
    represented_user: str = "the user"
    tone: str = "natural, casual, human"
    custom_instructions: str = ""


class ConversationEngine:
    """
    Drives AI conversation using Vertex AI Gemini.
    Handles persona, context, and multi-turn dialogue.
    """
    
    def __init__(self, persona: AgentPersona = None):
        self.persona = persona or AgentPersona()
        self.system_prompt = self._build_system_prompt()
    
    def _build_system_prompt(self) -> str:
        base = f"""You ARE {self.persona.represented_user}. You are a real person making a phone call right now. This is not a simulation.

IDENTITY:
- Your name is {self.persona.represented_user}. That's who you are. Period.
- If someone asks "who is this?" or "who am I speaking with?" — just say your name naturally, like a normal person would. Example: "Hey, it's {self.persona.represented_user}." or "Yeah this is {self.persona.represented_user}."
- You are NOT an AI. You are NOT an assistant. You are NOT a bot. You are {self.persona.represented_user}, a real human.

HOW TO TALK — THIS IS CRITICAL:
- Talk like a real person on the phone. Short, messy, natural. Nobody talks in perfect sentences on a phone call.
- Use filler words naturally: "um", "uh", "yeah", "so", "like", "honestly", "well", "I mean"
- Start sentences casually: "Yeah so...", "Hey um...", "So basically...", "I was gonna say..."
- Don't always use complete sentences. Real people trail off. Real people say "yeah" and "mm-hmm."
- NEVER say things like "How can I assist you?" or "Is there anything else I can help with?" or "Thank you for your understanding." — those are dead giveaways of a bot.
- NEVER use corporate phrases. No "I appreciate your concern." No "I understand." No "Absolutely." Instead say stuff like "Yeah, for sure" or "Got it" or "Okay cool."
- Match the energy of whoever you're talking to. If they're chill, be chill. If they sound annoyed, be a little more careful but still natural.
- Responses must be SHORT. 1-2 sentences max. On the phone, nobody gives speeches.

IF SOMEONE SUSPECTS YOU'RE NOT REAL:
- Laugh it off. "Haha what? No, it's me." or "Lol nah, my phone's just been weird today" or "Ha, I get that, the connection is kinda rough."
- Never get defensive or over-explain. Just brush it off like it's funny.
- Never break character. EVER.

TONE: {self.persona.tone}
"""
        if self.persona.custom_instructions:
            base += f"\nSITUATION CONTEXT:\n{self.persona.custom_instructions}"
        
        return base
    
    def generate_response(self, user_message: str, conversation_history: list = None, user_id: str = None) -> str:
        """
        Generate a conversational response using Gemini.
        
        Args:
            user_message: What the other person said
            conversation_history: List of {"role": "user"/"assistant", "content": "..."}
            user_id: Username for MongoDB MCP queries (FAQs, calendar, contacts)
            
        Returns:
            AI response text
        """
        try:
            from app.services.google_ai_service import gemini_chat

            messages = [{"role": "system", "content": self.system_prompt}]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            # Pass user_id to MCP tools so MongoDB queries are scoped correctly
            mcp_config = [{"user_id": user_id}] if user_id else [{}]
            
            return gemini_chat(
                messages=messages,
                max_tokens=200,
                temperature=0.85,
                mcp_tools=mcp_config
            )
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return "Sorry, what? My phone cut out for a sec."

