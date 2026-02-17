"""
Voice Profile models for Rain Check.
Maintains metadata for custom voice twins.
"""

from datetime import datetime
from typing import Optional, List, Dict
from pymongo import MongoClient
import logging

logger = logging.getLogger(__name__)

# Lazy DB initialization
_db = None

def _get_db():
    global _db
    if _db is None:
        from app.config import MONGODB_URI
        _db = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000).raincheck
    return _db

class VoiceProfile:
    """
    Metadata for a cloned or pre-built voice model.
    """
    
    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = _get_db().voice_profiles
            except Exception as e:
                logger.warning(f"MongoDB unavailable: {e}")
                raise
        return self._collection

    def create_profile(self, voice_id: str, name: str, user_id: str = "default") -> str:
        """Create a new voice profile record."""
        profile = {
            "voice_id": voice_id,
            "name": name,
            "user_id": user_id,
            "status": "active",
            "characteristics": {
                "tone": "unknown",
                "delivery": "natural"
            },
            "sample_count": 0,
            "created_at": datetime.utcnow()
        }
        result = self.collection.insert_one(profile)
        return str(result.inserted_id)

    def get_profile(self, voice_id: str) -> Optional[Dict]:
        """Retrieve profile by voice_id."""
        return self.collection.find_one({"voice_id": voice_id})

    def list_user_voices(self, user_id: str = "default") -> List[Dict]:
        """List all voices for a user."""
        return list(self.collection.find({"user_id": user_id}).sort("created_at", -1))

    def update_characteristics(self, voice_id: str, characteristics: Dict) -> bool:
        """Update voice characteristics (e.g., tone, accent)."""
        result = self.collection.update_one(
            {"voice_id": voice_id},
            {"$set": {"characteristics": characteristics}}
        )
        return result.modified_count > 0

    def delete_profile(self, voice_id: str) -> bool:
        """Delete profile metadata."""
        result = self.collection.delete_one({"voice_id": voice_id})
        return result.deleted_count > 0
