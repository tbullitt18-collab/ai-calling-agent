"""
Cloud-native scheduling service for Rain Check.
Persists scheduled calls in MongoDB and uses Google Cloud Scheduler
to trigger them reliably, surviving Cloud Run cold starts and scale-to-zero.
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class CallScheduler:
    """
    Manages scheduled outbound calls using MongoDB for persistence
    and Google Cloud Scheduler for reliable triggering.
    
    Falls back to an immediate-execution mode if Cloud Scheduler
    is unavailable (e.g., local dev).
    """
    
    def __init__(self):
        self._db = None
        self._collection = None
        self._cloud_scheduler = None
        self._initialized = False
    
    def _ensure_init(self):
        """Lazy-initialize MongoDB and Cloud Scheduler connections."""
        if self._initialized:
            return
        
        try:
            from pymongo import MongoClient
            from app.config import MONGODB_URI
            client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=3000)
            self._db = client.raincheck
            self._collection = self._db.scheduled_calls
            # Create TTL index to auto-clean old jobs after 24 hours
            self._collection.create_index("scheduled_time", expireAfterSeconds=86400)
            logger.info("CallScheduler connected to MongoDB (scheduled_calls collection)")
        except Exception as e:
            logger.warning(f"CallScheduler MongoDB init failed: {e}")
        
        try:
            from google.cloud import scheduler_v1
            self._cloud_scheduler = scheduler_v1.CloudSchedulerClient()
            logger.info("Google Cloud Scheduler client initialized")
        except Exception as e:
            logger.warning(f"Cloud Scheduler unavailable (will use fallback): {e}")
        
        self._initialized = True
    
    def start(self):
        """No-op for compatibility. Cloud-native scheduling doesn't need a thread."""
        logger.info("CallScheduler started (cloud-native mode, no background thread)")
    
    def stop(self):
        """No-op for compatibility."""
        pass

    def schedule_call(self, to_number: str, time_str: str, reason: str = None,
                      notes: str = None, voice_id: str = None) -> str:
        """
        Schedule a call at a specific time (HH:MM format, 24h).
        
        Persists the job to MongoDB so it survives container restarts.
        Attempts to create a Google Cloud Scheduler job for reliable triggering.
        If Cloud Scheduler is unavailable, registers a fallback check endpoint.
        
        Args:
            to_number: Destination phone number (E.164)
            time_str: Time in "HH:MM" 24-hour format
            reason: Reason for absence
            notes: Additional call notes
            voice_id: Voice twin ID to use
            
        Returns:
            job_id string
        """
        self._ensure_init()
        
        job_id = f"call_{int(time.time())}_{uuid.uuid4().hex[:8]}"
        
        # Parse the target time for today (or tomorrow if time already passed)
        now = datetime.utcnow()
        hour, minute = map(int, time_str.split(':'))
        scheduled_dt = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        # If the time already passed today, schedule for tomorrow
        if scheduled_dt <= now:
            scheduled_dt += timedelta(days=1)
        
        job_doc = {
            "job_id": job_id,
            "to_number": to_number,
            "scheduled_time": scheduled_dt,
            "time_str": time_str,
            "reason": reason,
            "notes": notes,
            "voice_id": voice_id,
            "status": "pending",
            "created_at": now,
        }
        
        # Persist to MongoDB
        if self._collection is not None:  # explicit None check — PyMongo collections don't support bool()
            self._collection.insert_one(job_doc)
            logger.info(f"Scheduled call persisted to MongoDB: {job_id} → {to_number} at {scheduled_dt.isoformat()}")
        else:
            logger.warning(f"MongoDB unavailable — scheduled call {job_id} is volatile (in-memory only)")
        
        # Attempt to create a Cloud Scheduler job
        self._create_cloud_scheduler_job(job_id, scheduled_dt)
        
        return job_id
    
    def _create_cloud_scheduler_job(self, job_id: str, scheduled_dt: datetime):
        """Create a one-time Cloud Scheduler HTTP job that hits our /session/execute-pending endpoint."""
        if not self._cloud_scheduler:
            logger.info("Cloud Scheduler not available — relying on polling fallback")
            return
        
        try:
            from app.config import BASE_URL
            from google.cloud import scheduler_v1
            import os
            
            project = os.getenv('GOOGLE_CLOUD_PROJECT', 'raincheck-prod-2026')
            location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
            parent = f"projects/{project}/locations/{location}"
            
            # Cloud Scheduler cron: run once at the scheduled minute
            cron = f"{scheduled_dt.minute} {scheduled_dt.hour} {scheduled_dt.day} {scheduled_dt.month} *"
            
            job = scheduler_v1.Job(
                name=f"{parent}/jobs/{job_id}",
                schedule=cron,
                time_zone="UTC",
                http_target=scheduler_v1.HttpTarget(
                    uri=f"{BASE_URL}/session/execute-pending",
                    http_method=scheduler_v1.HttpMethod.POST,
                    headers={
                        "Content-Type": "application/json",
                        "X-CloudScheduler-Secret": os.getenv('SCHEDULER_SECRET', 'raincheck-default-scheduler-secret')
                    },
                ),
                attempt_deadline={"seconds": 30},
            )
            
            self._cloud_scheduler.create_job(parent=parent, job=job)
            logger.info(f"Cloud Scheduler job created: {job_id} cron='{cron}'")
        except Exception as e:
            logger.warning(f"Cloud Scheduler job creation failed (non-fatal): {e}")
    
    def execute_pending_calls(self) -> list:
        """
        Check MongoDB for any pending calls whose scheduled_time has passed,
        execute them, and mark them as completed.
        
        Returns list of executed job_ids.
        """
        self._ensure_init()
        
        if self._collection is None:
            logger.warning("MongoDB unavailable — cannot execute pending calls")
            return []
        
        now = datetime.utcnow()
        executed = []
        
        # Find all pending calls that should have fired by now
        pending = self._collection.find({
            "status": "pending",
            "scheduled_time": {"$lte": now}
        })
        
        for job in pending:
            job_id = job["job_id"]
            logger.info(f"Executing pending scheduled call: {job_id} → {job['to_number']}")
            
            try:
                from app.services.vonage_service import initiate_outbound_call
                initiate_outbound_call(
                    job["to_number"],
                    reason=job.get("reason"),
                    notes=job.get("notes"),
                    voice_id=job.get("voice_id")
                )
                
                self._collection.update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "completed", "executed_at": now}}
                )
                executed.append(job_id)
                logger.info(f"Scheduled call executed successfully: {job_id}")
                
            except Exception as e:
                logger.error(f"Failed to execute scheduled call {job_id}: {e}")
                self._collection.update_one(
                    {"job_id": job_id},
                    {"$set": {"status": "failed", "error": str(e)}}
                )
        
        return executed
    
    def get_pending_calls(self) -> list:
        """Get all pending scheduled calls."""
        self._ensure_init()
        
        if self._collection is None:
            return []
        
        calls = list(self._collection.find(
            {"status": "pending"},
            {"_id": 0}
        ).sort("scheduled_time", 1))
        
        return calls
    
    def cancel_call(self, job_id: str) -> bool:
        """Cancel a pending scheduled call."""
        self._ensure_init()
        
        if self._collection is None:
            return False
        
        result = self._collection.update_one(
            {"job_id": job_id, "status": "pending"},
            {"$set": {"status": "cancelled"}}
        )
        
        if result.modified_count > 0:
            logger.info(f"Cancelled scheduled call: {job_id}")
            # Also try to delete the Cloud Scheduler job
            self._delete_cloud_scheduler_job(job_id)
            return True
        return False
    
    def _delete_cloud_scheduler_job(self, job_id: str):
        """Delete a Cloud Scheduler job (best-effort)."""
        if not self._cloud_scheduler:
            return
        try:
            import os
            project = os.getenv('GOOGLE_CLOUD_PROJECT', 'raincheck-prod-2026')
            location = os.getenv('GOOGLE_CLOUD_LOCATION', 'us-central1')
            name = f"projects/{project}/locations/{location}/jobs/{job_id}"
            self._cloud_scheduler.delete_job(name=name)
            logger.info(f"Deleted Cloud Scheduler job: {job_id}")
        except Exception as e:
            logger.warning(f"Could not delete Cloud Scheduler job {job_id}: {e}")
