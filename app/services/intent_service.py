"""
Intent Detection Service for Rain Check.
Uses OpenAI GPT to identify caller intents from speech.
"""

import json
import logging
from dataclasses import dataclass
from openai import OpenAI

logger = logging.getLogger(__name__)

_client = None


def _get_client():
    global _client
    if _client is None:
        from app.config import OPENAI_API_KEY
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client


@dataclass
class IntentResult:
    """Result of intent detection."""
    intent: str
    confidence: float
    needs_clarification: bool = False
    clarifying_question: str = ""
    entities: dict = None
    
    def __post_init__(self):
        if self.entities is None:
            self.entities = {}


INTENT_SYSTEM_PROMPT = """You are an intent detection system for a voice AI calling application.
Analyze the user's message and return a JSON object with these fields:
{
    "intent": "one of: greeting, sick_day, emergency, schedule_change, task_handoff, farewell, question, acknowledgment, unknown",
    "confidence": 0.0 to 1.0,
    "needs_clarification": true/false,
    "clarifying_question": "only if needs_clarification is true",
    "entities": {"key": "value"} 
}

Entity keys to extract when relevant:
- "duration": how long they'll be out
- "return_date": when they expect to return
- "reason": specific reason given
- "tasks": any tasks mentioned
- "urgency": low/medium/high

RESPOND WITH ONLY THE JSON OBJECT. No other text."""


def detect_intent(message: str, context: dict = None) -> IntentResult:
    """
    Detect intent from a message.
    
    Args:
        message: The user's spoken message
        context: Optional conversation context
        
    Returns:
        IntentResult with detected intent and entities
    """
    try:
        messages = [{"role": "system", "content": INTENT_SYSTEM_PROMPT}]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context: {json.dumps(context)}"
            })
        
        messages.append({"role": "user", "content": message})
        
        response = _get_client().chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=200,
            temperature=0.1,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        
        return IntentResult(
            intent=result.get("intent", "unknown"),
            confidence=result.get("confidence", 0.5),
            needs_clarification=result.get("needs_clarification", False),
            clarifying_question=result.get("clarifying_question", ""),
            entities=result.get("entities", {})
        )
        
    except Exception as e:
        logger.error(f"Intent detection error: {e}")
        return IntentResult(
            intent="unknown",
            confidence=0.0,
            needs_clarification=True,
            clarifying_question="Could you repeat that?"
        )
