"""
User Profile model for Rain Check.
Handles permanent display name, employee setup, and schedule info.
"""

from datetime import datetime
from typing import Optional, Dict
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


class UserProfile:
    """
    User profile with permanent display name and workplace setup info.
    """

    def __init__(self):
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            try:
                self._collection = _get_db().user_profiles
            except Exception as e:
                logger.warning(f"MongoDB unavailable: {e}")
                raise
        return self._collection

    def get_profile(self, username: str) -> Optional[Dict]:
        """Get user profile by username."""
        profile = self.collection.find_one({"username": username})
        if profile:
            profile['_id'] = str(profile['_id'])
        return profile

    def set_display_name(self, username: str, display_name: str) -> Dict:
        """
        Set a permanent display name for the user.
        Once set, it CANNOT be changed.
        Returns the profile dict or raises ValueError if already set.
        """
        existing = self.collection.find_one({"username": username})

        if existing and existing.get('display_name'):
            raise ValueError("Display name is permanent and has already been set.")

        if existing:
            self.collection.update_one(
                {"username": username},
                {"$set": {
                    "display_name": display_name,
                    "display_name_set_at": datetime.utcnow()
                }}
            )
        else:
            self.collection.insert_one({
                "username": username,
                "display_name": display_name,
                "display_name_set_at": datetime.utcnow(),
                "setup": {},
                "created_at": datetime.utcnow()
            })

        return self.get_profile(username)

    def update_setup(self, username: str, setup_data: Dict) -> Dict:
        """
        Update workplace setup info (schedule, employee ID, etc.).
        This CAN be updated at any time.
        """
        allowed_fields = {
            'employee_id', 'department', 'position', 'manager_name',
            'manager_number', 'shift_start', 'shift_end',
            'work_days', 'company_name', 'location', 'notes'
        }

        # Filter to only allowed fields
        filtered = {k: v for k, v in setup_data.items() if k in allowed_fields}

        existing = self.collection.find_one({"username": username})
        if existing:
            self.collection.update_one(
                {"username": username},
                {"$set": {
                    "setup": filtered,
                    "setup_updated_at": datetime.utcnow()
                }}
            )
        else:
            self.collection.insert_one({
                "username": username,
                "display_name": None,
                "setup": filtered,
                "setup_updated_at": datetime.utcnow(),
                "created_at": datetime.utcnow()
            })

        return self.get_profile(username)

    def has_display_name(self, username: str) -> bool:
        """Check if user has already set a permanent display name."""
        profile = self.collection.find_one({"username": username})
        return bool(profile and profile.get('display_name'))

    def is_setup_complete(self, username: str) -> bool:
        """Check if the user has completed basic setup."""
        profile = self.collection.find_one({"username": username})
        if not profile or not profile.get('setup'):
            return False
        setup = profile['setup']
        # At minimum, employee_id and manager_number should be set
        return bool(setup.get('employee_id') and setup.get('manager_number'))
