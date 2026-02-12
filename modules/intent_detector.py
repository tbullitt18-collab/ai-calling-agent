"""
Intent detection and follow-up question generation for Rain Check.
Uses Anthropic Claude to understand caller intent and generate clarifying questions.
"""

import os
import json
import anthropic
from typing import Optional, Tuple
from dataclasses import dataclass
from config import CLAUDE_API_KEY

# Initialize Anthropic client
client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)


@dataclass
class IntentResult:
    intent: str
    confidence: float
    needs_clarification: bool
    clarifying_question: Optional[str] = None
    entities: dict = None


INTENT_SYSTEM_PROMPT = """You are an intent detection system for Rain Check, an AI voice assistant.

Analyze the user's message and return a JSON object with:
1. "intent": The primary intent category (e.g., "inquiry", "appointment", "complaint", "support", "general_chat", "unclear")
2. "confidence": A float 0-1 indicating confidence in the detection
3. "needs_clarification": Boolean, true if the message is vague or ambiguous
4. "clarifying_question": If needs_clarification is true, provide a natural follow-up question (under 20 words)
5. "entities": Any extracted entities (names, dates, numbers, topics)

Examples of good clarifying questions:
- "Could you tell me more about what specific issue you're experiencing?"
- "I'd love to help with that. What timeframe works best for you?"

Output valid JSON only. Do not include any explanation."""


def detect_intent(
    user_message: str,
    conversation_history: list[dict] = None
) -> IntentResult:
    """
    Detect user intent and generate follow-up questions if needed.
    """
    messages = []
    
    # Add conversation history for context (last 3 turns)
    if conversation_history:
        for turn in conversation_history[-6:]:
            role = "user" if turn["role"] == "user" else "assistant"
            messages.append({
                "role": role,
                "content": turn["content"]
            })
            
    # Add current user message
    messages.append({
        "role": "user", 
        "content": f"Analyze this message: \"{user_message}\". Return JSON."
    })
    
    try:
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=500,
            system=INTENT_SYSTEM_PROMPT,
            messages=messages,
            temperature=0.0
        )
        
        # Extract JSON from response
        content = response.content[0].text
        # Naive JSON extraction (Claude is usually good at outputting raw JSON if asked)
        result = json.loads(content)
        
    except Exception as e:
        print(f"Intent detection error: {e}")
        # Fallback result
        result = {}
    
    return IntentResult(
        intent=result.get("intent", "unclear"),
        confidence=result.get("confidence", 0.5),
        needs_clarification=result.get("needs_clarification", False),
        clarifying_question=result.get("clarifying_question"),
        entities=result.get("entities", {})
    )


def should_ask_followup(intent_result: IntentResult) -> Tuple[bool, str]:
    """
    Determine if a follow-up question should be asked.
    """
    if intent_result.needs_clarification and intent_result.clarifying_question:
        return True, intent_result.clarifying_question
        
    if intent_result.confidence < 0.6:
        return True, "I want to make sure I understand you correctly. Could you expand on that?"
        
    return False, ""
