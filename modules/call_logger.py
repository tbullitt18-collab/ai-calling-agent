"""
Call logging and analytics for Rain Check.
Stores transcripts and generates summaries for QA.
"""

from pymongo import MongoClient
from datetime import datetime
from typing import Optional, List, Dict, Any
import anthropic

# Lazy initialization
_mongo_client = None
_db = None
_anthropic_client = None


def _get_db():
    """Get or create MongoDB connection."""
    global _mongo_client, _db
    if _db is None:
        from config import MONGODB_URI
        _mongo_client = MongoClient(MONGODB_URI)
        _db = _mongo_client.raincheck
    return _db


def _get_anthropic():
    """Get or create Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        from config import CLAUDE_API_KEY
        _anthropic_client = anthropic.Anthropic(api_key=CLAUDE_API_KEY)
    return _anthropic_client


class CallLogger:
    """
    Handles call logging, summarization, and analytics.
    
    Stores complete call transcripts in MongoDB and generates
    AI-powered summaries for quality assurance.
    """
    
    def __init__(self):
        """Initialize CallLogger with database collections."""
        db = _get_db()
        self.calls_collection = db.calls
        self.analytics_collection = db.analytics
        
    def log_call(self, session) -> str:
        """
        Log a completed call with full transcript and summary.
        
        Args:
            session: CallSession object from session_manager
            
        Returns:
            The inserted document ID
        """
        # Generate transcript text
        transcript_text = "\n".join([
            f"{t.role}: {t.content}"
            for t in session.conversation
        ])
        
        # Generate AI summary
        summary = self._generate_summary(transcript_text)
        
        # Calculate metrics
        duration_seconds = self._calculate_duration(session)
        turn_count = len(session.conversation)
        
        document = {
            "call_uuid": session.call_uuid,
            "caller_number": session.caller_number,
            "started_at": session.started_at,
            "ended_at": datetime.utcnow().isoformat(),
            "duration_seconds": duration_seconds,
            "turn_count": turn_count,
            "detected_intent": session.intent,
            "sentiment": session.sentiment,
            "transcript": [
                {
                    "role": t.role,
                    "content": t.content,
                    "timestamp": t.timestamp
                }
                for t in session.conversation
            ],
            "summary": summary,
            "metadata": session.metadata,
            "created_at": datetime.utcnow()
        }
        
        result = self.calls_collection.insert_one(document)
        
        # Update aggregate analytics
        self._update_analytics(document)
        
        return str(result.inserted_id)
        
    def get_call(self, call_uuid: str) -> Optional[Dict]:
        """
        Retrieve a logged call by UUID.
        
        Args:
            call_uuid: The call's unique identifier
            
        Returns:
            Call document or None
        """
        return self.calls_collection.find_one({"call_uuid": call_uuid})
        
    def get_call_history(
        self,
        caller_number: str,
        limit: int = 10
    ) -> List[Dict]:
        """
        Retrieve call history for a specific caller.
        
        Args:
            caller_number: Caller's phone number
            limit: Maximum number of calls to return
            
        Returns:
            List of call documents (without full transcript)
        """
        return list(
            self.calls_collection.find(
                {"caller_number": caller_number},
                {"transcript": 0}  # Exclude full transcript for list view
            ).sort("created_at", -1).limit(limit)
        )
        
    def get_recent_calls(self, limit: int = 50) -> List[Dict]:
        """
        Get most recent calls across all callers.
        
        Args:
            limit: Maximum number of calls to return
            
        Returns:
            List of recent call documents
        """
        return list(
            self.calls_collection.find(
                {},
                {"transcript": 0}
            ).sort("created_at", -1).limit(limit)
        )
        
    def get_analytics(self, date: str = None) -> Optional[Dict]:
        """
        Get analytics for a specific date.
        
        Args:
            date: Date string (YYYY-MM-DD), defaults to today
            
        Returns:
            Analytics document or None
        """
        if date is None:
            date = datetime.utcnow().strftime("%Y-%m-%d")
        return self.analytics_collection.find_one({"date": date})
        
    def get_analytics_range(
        self,
        start_date: str,
        end_date: str
    ) -> List[Dict]:
        """
        Get analytics for a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of analytics documents
        """
        return list(
            self.analytics_collection.find({
                "date": {"$gte": start_date, "$lte": end_date}
            }).sort("date", 1)
        )
        
    def _generate_summary(self, transcript: str) -> str:
        """Generate a concise summary of the call transcript using Claude."""
        if not transcript.strip():
            return "No conversation recorded."
            
        try:
            client = _get_anthropic()
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=200,
                system="Summarize this call transcript in 2-3 sentences. Focus on: caller's main need, resolution status, and any follow-up required.",
                messages=[{"role": "user", "content": transcript}],
                temperature=0.3
            )
            return response.content[0].text
            
        except Exception as e:
            print(f"Error generating summary: {e}")
            return "Summary generation failed."
            
    def _calculate_duration(self, session) -> int:
        """Calculate call duration in seconds."""
        if not session.conversation:
            return 0
            
        try:
            start = datetime.fromisoformat(session.started_at)
            end = datetime.fromisoformat(session.conversation[-1].timestamp)
            return int((end - start).total_seconds())
        except:
            return 0
            
    def _update_analytics(self, call_doc: Dict) -> None:
        """Update aggregate analytics with new call data."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        
        update = {
            "$inc": {
                "total_calls": 1,
                "total_duration": call_doc.get("duration_seconds", 0),
                "total_turns": call_doc.get("turn_count", 0)
            },
            "$setOnInsert": {
                "date": today
            }
        }
        
        if call_doc.get("detected_intent"):
            update["$push"] = {"intents": call_doc["detected_intent"]}
            
        self.analytics_collection.update_one(
            {"date": today},
            update,
            upsert=True
        )


# Convenience instance
_call_logger = None


def get_call_logger() -> CallLogger:
    """Get or create the default CallLogger instance."""
    global _call_logger
    if _call_logger is None:
        _call_logger = CallLogger()
    return _call_logger
