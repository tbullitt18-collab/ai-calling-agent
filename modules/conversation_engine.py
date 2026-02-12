"""
Conversation engine for Rain Check.
Generates contextual, persona-aware responses using Anthropic Claude.
"""

import anthropic
from typing import List, Dict, Optional
from dataclasses import dataclass
from config import CLAUDE_API_KEY

client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


@dataclass
class AgentPersona:
    """Configuration for the AI agent's personality."""
    name: str = "Rain Check"
    warmth: float = 0.8
    confidence: float = 0.7
    empathy: float = 0.9
    tone: str = "friendly"
    custom_instructions: str = ""
    

class ConversationEngine:
    """
    Generates AI responses with personality and context awareness using Claude.
    """
    
    def __init__(self, persona: AgentPersona = None):
        self.persona = persona or AgentPersona()
        self.system_prompt = self._build_system_prompt()
        
    def _build_system_prompt(self) -> str:
        """Build system prompt based on persona configuration."""
        warmth = "warm and caring" if self.persona.warmth > 0.5 else "professional"
        
        return f"""You are {self.persona.name}, an AI voice assistant on a phone call.

PERSONALITY:
- You are {warmth} and {self.persona.tone}.
- Speak naturally with contractions and casual phrasing.
- Mirror the caller's energy.
- Keep responses CONCISE (under 2 sentences) unless explaining a process.
- Never mention being an AI unless asked.

{self.persona.custom_instructions}"""

    def generate_response(
        self,
        user_message: str,
        conversation_history: List[Dict[str, str]] = None,
        max_tokens: int = 150
    ) -> str:
        """
        Generate a contextual response to the user's message.
        """
        messages = []
        
        if conversation_history:
            for turn in conversation_history[-10:]:
                role = "user" if turn["role"] == "user" else "assistant"
                messages.append({
                    "role": role,
                    "content": turn["content"]
                })
                
        messages.append({"role": "user", "content": user_message})
        
        try:
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=max_tokens,
                system=self.system_prompt,
                messages=messages,
                temperature=0.7
            )
            return response.content[0].text
            
        except Exception as e:
            print(f"Error generating response: {e}")
            return "I'm having a bit of trouble hearing you. Could you say that again?"

    def update_persona(self, persona: AgentPersona) -> None:
        self.persona = persona
        self.system_prompt = self._build_system_prompt()
