"""
Session management for Rain Check calls.
Maintains conversation context using Redis for sub-millisecond access.
Falls back to in-memory storage if Redis is unavailable.
"""

import json
import logging
from typing import Optional, List, Dict, Any

logger = logging.getLogger(__name__)
from dataclasses import dataclass, asdict, field
from datetime import datetime

# Try to import redis, fall back to in-memory if unavailable
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class ConversationTurn:
    """A single turn in a conversation."""
    role: str  # "user" or "assistant"
    content: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class CallSession:
    """Complete session state for a phone call."""
    call_uuid: str
    caller_number: str
    started_at: str
    conversation: List[ConversationTurn] = field(default_factory=list)
    intent: Optional[str] = None
    sentiment: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class InMemoryStore:
    """Simple in-memory key-value store for development."""
    
    def __init__(self):
        self._store = {}
        
    def get(self, key: str) -> Optional[str]:
        return self._store.get(key)
        
    def setex(self, key: str, ttl: int, value: str) -> None:
        self._store[key] = value
        
    def delete(self, key: str) -> int:
        if key in self._store:
            del self._store[key]
            return 1
        return 0


class SessionManager:
    """
    Manages call sessions with Redis for fast context retrieval.
    Falls back to in-memory storage if Redis is unavailable.
    
    Each call has its own session that persists conversation history,
    detected intents, and other metadata throughout the call lifecycle.
    """
    
    def __init__(self, redis_url: str = None):
        """
        Initialize SessionManager with Redis connection.
        
        Args:
            redis_url: Redis connection URL (defaults to config value)
        """
        self.ttl = 3600 * 24  # 24 hour session TTL
        self._use_redis = False
        
        if REDIS_AVAILABLE:
            try:
                if redis_url is None:
                    from app.config import REDIS_URL
                    redis_url = REDIS_URL
                    
                self.redis = redis.from_url(redis_url, decode_responses=True)
                # Test connection
                self.redis.ping()
                self._use_redis = True
                logger.info("Connected to Redis for session management")
            except Exception as e:
                logger.warning(f"Redis unavailable ({e}), using in-memory storage")
                self.redis = InMemoryStore()
                # If Redis connection fails, ensure _use_redis is False for context methods
                self._use_redis = False
        else:
            logger.warning("Redis package not installed, using in-memory storage")
            self.redis = InMemoryStore()
            self._use_redis = False # Explicitly set if Redis package is not installed
        
        # Initialize a local in-memory store for context fallback, separate from InMemoryStore for sessions
        self._memory_db = {} if not self._use_redis else None

    def set_context(self, call_sid: str, context: dict, ex: int = 3600):
        """Store call context with expiration."""
        if self._use_redis:
            try:
                self.redis.setex(f"context:{call_sid}", ex, json.dumps(context))
                return
            except Exception as e:
                logger.warning(f"Redis setex failed for context:{call_sid} ({e}). Falling back to in-memory.")
        
        # Fallback to memory
        if self._memory_db is not None:
            self._memory_db[f"context:{call_sid}"] = json.dumps(context)

    def get_context(self, call_sid: str) -> Optional[dict]:
        """Retrieve call context."""
        data = None
        if self._use_redis:
            try:
                data = self.redis.get(f"context:{call_sid}")
            except Exception as e:
                logger.warning(f"Redis get failed for context:{call_sid} ({e}). Falling back to in-memory.")
        
        if not data and self._memory_db is not None:
            data = self._memory_db.get(f"context:{call_sid}")
            
        return json.loads(data) if data else None
        
    def create_session(self, call_uuid: str, caller_number: str) -> CallSession:
        """
        Create a new call session.
        
        Args:
            call_uuid: Unique identifier for the call
            caller_number: Caller's phone number
            
        Returns:
            Newly created CallSession
        """
        session = CallSession(
            call_uuid=call_uuid,
            caller_number=caller_number,
            started_at=datetime.utcnow().isoformat(),
            conversation=[]
        )
        self._save_session(session)
        return session
        
    def get_session(self, call_uuid: str) -> Optional[CallSession]:
        """
        Retrieve an existing session by call UUID.
        
        Args:
            call_uuid: The call's unique identifier
            
        Returns:
            CallSession if found, None otherwise
        """
        data = self.redis.get(f"session:{call_uuid}")
        if not data:
            return None
        return self._deserialize_session(json.loads(data))
        
    def add_turn(
        self,
        call_uuid: str,
        role: str,
        content: str
    ) -> Optional[CallSession]:
        """
        Add a conversation turn to the session.
        
        Args:
            call_uuid: The call's unique identifier
            role: Either "user" or "assistant"
            content: The message content
            
        Returns:
            Updated CallSession if found, None otherwise
        """
        session = self.get_session(call_uuid)
        if not session:
            return None
            
        turn = ConversationTurn(
            role=role,
            content=content,
            timestamp=datetime.utcnow().isoformat()
        )
        session.conversation.append(turn)
        self._save_session(session)
        return session
        
    def update_intent(self, call_uuid: str, intent: str) -> None:
        """
        Update the detected intent for a session.
        
        Args:
            call_uuid: The call's unique identifier
            intent: Detected intent category
        """
        session = self.get_session(call_uuid)
        if session:
            session.intent = intent
            self._save_session(session)
            
    def update_sentiment(self, call_uuid: str, sentiment: str) -> None:
        """
        Update the detected sentiment for a session.
        
        Args:
            call_uuid: The call's unique identifier
            sentiment: Detected sentiment (positive, negative, neutral)
        """
        session = self.get_session(call_uuid)
        if session:
            session.sentiment = sentiment
            self._save_session(session)
            
    def set_metadata(self, call_uuid: str, key: str, value: Any) -> None:
        """
        Set a metadata value on the session.
        
        Args:
            call_uuid: The call's unique identifier
            key: Metadata key
            value: Metadata value (must be JSON serializable)
        """
        session = self.get_session(call_uuid)
        if session:
            session.metadata[key] = value
            self._save_session(session)
            
    def get_conversation_history(
        self,
        call_uuid: str,
        max_turns: int = None
    ) -> List[Dict[str, str]]:
        """
        Get conversation history formatted for LLM input.
        
        Args:
            call_uuid: The call's unique identifier
            max_turns: Maximum number of turns to return (None = all)
            
        Returns:
            List of conversation turns as dicts
        """
        session = self.get_session(call_uuid)
        if not session:
            return []
            
        history = [
            {"role": turn.role, "content": turn.content}
            for turn in session.conversation
        ]
        
        if max_turns:
            return history[-max_turns:]
        return history
        
    def delete_session(self, call_uuid: str) -> bool:
        """
        Delete a session.
        
        Args:
            call_uuid: The call's unique identifier
            
        Returns:
            True if deleted, False if not found
        """
        return self.redis.delete(f"session:{call_uuid}") > 0
        
    def _save_session(self, session: CallSession) -> None:
        """Persist session to Redis with TTL."""
        data = {
            **asdict(session),
            "conversation": [asdict(t) for t in session.conversation]
        }
        self.redis.setex(
            f"session:{session.call_uuid}",
            self.ttl,
            json.dumps(data)
        )
        
    def _deserialize_session(self, data: dict) -> CallSession:
        """Reconstruct CallSession from Redis data."""
        data["conversation"] = [
            ConversationTurn(**t) for t in data.get("conversation", [])
        ]
        return CallSession(**data)


# Convenience instance for direct import
_session_manager = None


def get_session_manager() -> SessionManager:
    """Get or create the default SessionManager instance."""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
