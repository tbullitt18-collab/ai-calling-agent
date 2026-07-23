"""
MongoDB MCP Service for Rain Check.
Provides real database query functions for Gemini's function calling.
Connects to MongoDB Atlas and exposes calendar, FAQ, and contact lookups.
"""

import re
import logging
from datetime import datetime
from typing import Optional

from pymongo import MongoClient
from bson.objectid import ObjectId

logger = logging.getLogger(__name__)

_mcp_service = None


def get_mcp_service():
    """Get or create the MongoDBMCPService singleton."""
    global _mcp_service
    if _mcp_service is None:
        _mcp_service = MongoDBMCPService()
    return _mcp_service


class MongoDBMCPService:
    """Provides MongoDB-backed knowledge base queries for the AI voice agent."""

    def __init__(self):
        try:
            from app.config import MONGODB_URI
            self.mongo = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            self.db = self.mongo.raincheck
            self.user_faqs = self.db.user_faqs
            self.user_calendar = self.db.user_calendar
            self.user_contacts = self.db.user_contacts
            logger.info("MongoDBMCPService connected to MongoDB")
        except Exception as e:
            logger.warning(f"MongoDB unavailable for MCP service: {e}")
            self.mongo = None
            self.user_faqs = None
            self.user_calendar = None
            self.user_contacts = None

    # ------------------------------------------------------------------
    # Gemini function-calling query methods
    # ------------------------------------------------------------------

    def search_calendar(self, user_id: str, query: str) -> str:
        """
        Search user_calendar for events matching the query string.

        Uses case-insensitive regex across title, description, and date fields.
        Returns a natural language summary of matching events, or
        'No events found.' if none match.  Limited to 5 results.
        """
        if self.user_calendar is None:
            return "Calendar service unavailable."

        try:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
            cursor = self.user_calendar.find({
                "user_id": user_id,
                "$or": [
                    {"title": {"$regex": pattern}},
                    {"description": {"$regex": pattern}},
                    {"date": {"$regex": pattern}},
                ],
            }).limit(5)

            events = list(cursor)
            if not events:
                return "No events found."

            lines = []
            for e in events:
                title = e.get("title", "Untitled")
                date = e.get("date", "No date")
                desc = e.get("description", "")
                line = f"- {title} on {date}"
                if desc:
                    line += f" ({desc})"
                lines.append(line)

            return "Here are the matching events:\n" + "\n".join(lines)

        except Exception as e:
            logger.error(f"search_calendar error: {e}")
            return "Error searching calendar."

    def query_faq(self, user_id: str, question: str) -> str:
        """
        Search user_faqs for FAQs matching keywords from the question.

        Uses case-insensitive regex on question and answer fields.
        Returns a natural language summary of matching FAQs, or
        'No matching FAQ found.' if empty.  Limited to 3 results.
        """
        if self.user_faqs is None:
            return "FAQ service unavailable."

        try:
            # Build an OR pattern from significant keywords (>2 chars)
            keywords = [w for w in question.split() if len(w) > 2]
            if not keywords:
                keywords = [question]

            pattern = re.compile("|".join(re.escape(k) for k in keywords), re.IGNORECASE)
            cursor = self.user_faqs.find({
                "user_id": user_id,
                "$or": [
                    {"question": {"$regex": pattern}},
                    {"answer": {"$regex": pattern}},
                ],
            }).limit(3)

            faqs = list(cursor)
            if not faqs:
                return "No matching FAQ found."

            lines = []
            for f in faqs:
                q = f.get("question", "")
                a = f.get("answer", "")
                lines.append(f"Q: {q}\nA: {a}")

            return "Here are the relevant FAQs:\n" + "\n\n".join(lines)

        except Exception as e:
            logger.error(f"query_faq error: {e}")
            return "Error searching FAQs."

    def lookup_contact(self, user_id: str, name: str) -> str:
        """
        Search user_contacts for contacts matching the name.

        Uses case-insensitive regex.  Returns contact details as a string,
        or 'Contact not found.' if empty.
        """
        if self.user_contacts is None:
            return "Contacts service unavailable."

        try:
            pattern = re.compile(re.escape(name), re.IGNORECASE)
            contact = self.user_contacts.find_one({
                "user_id": user_id,
                "name": {"$regex": pattern},
            })

            if not contact:
                return "Contact not found."

            parts = [f"Name: {contact.get('name', 'Unknown')}"]
            if contact.get("role"):
                parts.append(f"Role: {contact['role']}")
            if contact.get("phone"):
                parts.append(f"Phone: {contact['phone']}")
            if contact.get("email"):
                parts.append(f"Email: {contact['email']}")

            return ", ".join(parts)

        except Exception as e:
            logger.error(f"lookup_contact error: {e}")
            return "Error looking up contact."

    def book_calendar(self, user_id: str, title: str, date: str, description: str = "") -> str:
        """
        Inserts a new calendar event into the user's calendar collection.
        Returns a confirmation string for the LLM to read back to the caller.
        """
        try:
            event = {
                "user_id": user_id,
                "title": title,
                "date": date,           # Expect ISO string: "2026-07-24T15:00:00"
                "description": description,
                "created_at": datetime.utcnow().isoformat(),
                "source": "ai_calling_agent"
            }
            result = self.user_calendar.insert_one(event)
            return f"Successfully booked: '{title}' on {date}. Event ID: {str(result.inserted_id)}"
        except Exception as e:
            return f"Failed to book calendar event: {str(e)}"

    # ------------------------------------------------------------------
    # Demo data seeding
    # ------------------------------------------------------------------

    def seed_demo_data(self, user_id: str) -> dict:
        """
        Seed demo data for IBM hackathon judges.

        Uses update_one with upsert=True keyed on user_id + a unique field
        to avoid duplicates.  Returns counts of seeded items.
        """
        if self.user_calendar is None:
            return {"error": "MongoDB unavailable"}

        try:
            # --- Calendar events ---
            calendar_events = [
                {"title": "Team standup", "date": "Every weekday at 9 AM", "description": "Daily sync with the engineering team"},
                {"title": "Dentist appointment", "date": "Friday at 2 PM", "description": "Routine cleaning at Dr. Smith's office"},
                {"title": "Project deadline", "date": "Next Monday", "description": "Q3 dashboard migration final deliverable"},
            ]
            cal_count = 0
            for event in calendar_events:
                result = self.user_calendar.update_one(
                    {"user_id": user_id, "title": event["title"]},
                    {"$set": {**event, "user_id": user_id, "created_at": datetime.utcnow()}},
                    upsert=True,
                )
                if result.upserted_id or result.modified_count:
                    cal_count += 1

            # --- FAQs ---
            faqs = [
                {"question": "What's your email?", "answer": "todd@example.com"},
                {"question": "When do you usually take lunch?", "answer": "Around noon, 12-1 PM"},
                {"question": "What project are you working on?", "answer": "The Q3 dashboard migration"},
            ]
            faq_count = 0
            for faq in faqs:
                result = self.user_faqs.update_one(
                    {"user_id": user_id, "question": faq["question"]},
                    {"$set": {**faq, "user_id": user_id, "created_at": datetime.utcnow()}},
                    upsert=True,
                )
                if result.upserted_id or result.modified_count:
                    faq_count += 1

            # --- Contacts ---
            contacts = [
                {"name": "Sarah Johnson", "role": "Manager", "phone": "555-0101", "email": "sarah.johnson@example.com"},
                {"name": "Mike Chen", "role": "Teammate", "phone": "555-0102", "email": "mike.chen@example.com"},
            ]
            contact_count = 0
            for contact in contacts:
                result = self.user_contacts.update_one(
                    {"user_id": user_id, "name": contact["name"]},
                    {"$set": {**contact, "user_id": user_id, "created_at": datetime.utcnow()}},
                    upsert=True,
                )
                if result.upserted_id or result.modified_count:
                    contact_count += 1

            logger.info(f"Demo data seeded for user {user_id}: {cal_count} events, {faq_count} FAQs, {contact_count} contacts")
            return {
                "calendar_events": cal_count,
                "faqs": faq_count,
                "contacts": contact_count,
            }

        except Exception as e:
            return {"error": str(e)}

    def clear_knowledge_base(self, user_id: str) -> dict:
        """
        Clear all knowledge base data (calendar, FAQs, contacts) for a user.
        """
        if self.user_calendar is None:
            return {"error": "MongoDB unavailable"}

        try:
            cal_result = self.user_calendar.delete_many({"user_id": user_id})
            faq_result = self.user_faqs.delete_many({"user_id": user_id})
            contact_result = self.user_contacts.delete_many({"user_id": user_id})

            logger.info(f"Knowledge base cleared for user {user_id}: {cal_result.deleted_count} events, {faq_result.deleted_count} FAQs, {contact_result.deleted_count} contacts deleted")
            return {
                "calendar_events_deleted": cal_result.deleted_count,
                "faqs_deleted": faq_result.deleted_count,
                "contacts_deleted": contact_result.deleted_count,
            }
        except Exception as e:
            logger.error(f"clear_knowledge_base error: {e}")
            return {"error": str(e)}

    # ------------------------------------------------------------------
    # CRUD helpers
    # ------------------------------------------------------------------

    def get_faqs(self, user_id: str) -> list:
        """Return all FAQs for the user as a list of dicts."""
        if self.user_faqs is None:
            return []
        try:
            faqs = list(self.user_faqs.find({"user_id": user_id}))
            for f in faqs:
                f["_id"] = str(f["_id"])
            return faqs
        except Exception as e:
            logger.error(f"get_faqs error: {e}")
            return []

    def add_faq(self, user_id: str, question: str, answer: str) -> str:
        """Add a new FAQ. Returns the inserted ID as a string."""
        if self.user_faqs is None:
            return ""
        try:
            result = self.user_faqs.insert_one({
                "user_id": user_id,
                "question": question,
                "answer": answer,
                "created_at": datetime.utcnow(),
            })
            logger.info(f"FAQ added: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"add_faq error: {e}")
            return ""

    def delete_faq(self, user_id: str, faq_id: str) -> bool:
        """Delete an FAQ by ID."""
        if self.user_faqs is None:
            return False
        try:
            result = self.user_faqs.delete_one({"_id": ObjectId(faq_id), "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"delete_faq error: {e}")
            return False

    def get_calendar(self, user_id: str) -> list:
        """Return all calendar events for the user."""
        if self.user_calendar is None:
            return []
        try:
            events = list(self.user_calendar.find({"user_id": user_id}))
            for e in events:
                e["_id"] = str(e["_id"])
            return events
        except Exception as e:
            logger.error(f"get_calendar error: {e}")
            return []

    def add_calendar_event(self, user_id: str, title: str, date: str, description: str = "") -> str:
        """Add a calendar event. Returns the inserted ID as a string."""
        if self.user_calendar is None:
            return ""
        try:
            result = self.user_calendar.insert_one({
                "user_id": user_id,
                "title": title,
                "date": date,
                "description": description,
                "created_at": datetime.utcnow(),
            })
            logger.info(f"Calendar event added: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"add_calendar_event error: {e}")
            return ""

    def delete_calendar_event(self, user_id: str, event_id: str) -> bool:
        """Delete a calendar event by ID."""
        if self.user_calendar is None:
            return False
        try:
            result = self.user_calendar.delete_one({"_id": ObjectId(event_id), "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"delete_calendar_event error: {e}")
            return False

    def get_contacts(self, user_id: str) -> list:
        """Return all contacts for the user."""
        if self.user_contacts is None:
            return []
        try:
            contacts = list(self.user_contacts.find({"user_id": user_id}))
            for c in contacts:
                c["_id"] = str(c["_id"])
            return contacts
        except Exception as e:
            logger.error(f"get_contacts error: {e}")
            return []

    def add_contact(self, user_id: str, name: str, role: str, phone: str = "", email: str = "") -> str:
        """Add a contact. Returns the inserted ID as a string."""
        if self.user_contacts is None:
            return ""
        try:
            doc = {
                "user_id": user_id,
                "name": name,
                "role": role,
                "created_at": datetime.utcnow(),
            }
            if phone:
                doc["phone"] = phone
            if email:
                doc["email"] = email

            result = self.user_contacts.insert_one(doc)
            logger.info(f"Contact added: {result.inserted_id}")
            return str(result.inserted_id)
        except Exception as e:
            logger.error(f"add_contact error: {e}")
            return ""

    def delete_contact(self, user_id: str, contact_id: str) -> bool:
        """Delete a contact by ID."""
        if self.user_contacts is None:
            return False
        try:
            result = self.user_contacts.delete_one({"_id": ObjectId(contact_id), "user_id": user_id})
            return result.deleted_count > 0
        except Exception as e:
            logger.error(f"delete_contact error: {e}")
            return False

