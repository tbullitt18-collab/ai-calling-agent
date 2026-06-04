"""
Call Logger Service for Rain Check.
Logs call transcripts, generates summaries, and stores in MongoDB.
Uses Vertex AI Gemini for generating call summaries.
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_call_logger = None


def get_call_logger():
    """Get or create the CallLogger singleton."""
    global _call_logger
    if _call_logger is None:
        _call_logger = CallLogger()
    return _call_logger


class CallLogger:
    """Logs call data to MongoDB and generates AI summaries."""
    
    def __init__(self):
        try:
            from pymongo import MongoClient
            from app.config import MONGODB_URI
            self.mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            self.db = self.mongo.raincheck
            self.calls = self.db.calls
            self.analytics = self.db.analytics
            logger.info("CallLogger connected to MongoDB")
        except Exception as e:
            logger.warning(f"MongoDB unavailable: {e}. Call logging disabled.")
            self.mongo = None
            self.calls = None
            self.analytics = None
    
    def log_call(self, session) -> Optional[str]:
        """
        Log a call session to MongoDB.
        
        Args:
            session: CallSession object with conversation data
            
        Returns:
            MongoDB document ID or None
        """
        if not self.calls:
            logger.warning("MongoDB unavailable, skipping call log")
            return None
        
        try:
            transcript = session.get_transcript() if hasattr(session, 'get_transcript') else []
            summary = self._generate_summary(transcript) if transcript else "No conversation recorded"
            
            doc = {
                "call_uuid": session.call_uuid,
                "caller": getattr(session, 'caller', 'unknown'),
                "timestamp": datetime.utcnow(),
                "duration_seconds": getattr(session, 'duration', 0),
                "transcript": transcript,
                "summary": summary,
                "intent": getattr(session, 'detected_intent', 'unknown'),
                "sentiment": getattr(session, 'sentiment', 'neutral'),
                "status": "completed"
            }
            
            result = self.calls.insert_one(doc)
            logger.info(f"Call logged: {result.inserted_id}")
            return str(result.inserted_id)
            
        except Exception as e:
            logger.error(f"Call logging error: {e}")
            return None
    
    def _generate_summary(self, transcript: list) -> str:
        """Use Gemini to summarize a call transcript."""
        try:
            from app.services.google_ai_service import gemini_chat

            text = "\n".join([
                f"{'AI' if t.get('role') == 'assistant' else 'Manager'}: {t.get('content', '')}"
                for t in transcript
            ])
            
            response = gemini_chat(
                messages=[
                    {"role": "system", "content": "Summarize this phone call transcript in 2-3 sentences. Focus on: reason for call, outcome, and any follow-up needed."},
                    {"role": "user", "content": text}
                ],
                max_tokens=150,
                temperature=0.3,
            )
            
            return response
            
        except Exception as e:
            logger.error(f"Summary generation error: {e}")
            return "Summary unavailable"
    
    def get_call(self, call_uuid: str) -> Optional[dict]:
        """Get call by UUID."""
        if not self.calls:
            return None
        return self.calls.find_one({"call_uuid": call_uuid})
    
    def get_recent_calls(self, limit: int = 10) -> list:
        """Get recent calls sorted by timestamp."""
        if not self.calls:
            return []
        return list(
            self.calls.find()
                .sort("timestamp", -1)
                .limit(limit)
        )
    
    def get_analytics(self) -> Optional[dict]:
        """Get aggregate call analytics."""
        if not self.calls:
            return None
        
        try:
            pipeline = [
                {
                    "$group": {
                        "_id": "all",
                        "total_calls": {"$sum": 1},
                        "completed_calls": {
                            "$sum": {"$cond": [{"$eq": ["$status", "completed"]}, 1, 0]}
                        },
                        "total_duration_seconds": {"$sum": "$duration_seconds"}
                    }
                }
            ]
            results = list(self.calls.aggregate(pipeline))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Analytics error: {e}")
            return None
