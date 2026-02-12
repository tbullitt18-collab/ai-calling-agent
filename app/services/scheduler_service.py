"""
Background scheduling service for Rain Check.
Handles automated calls at specific times (e.g., 6:00 AM sick calls).
"""

import schedule
import time
import threading
import logging
from datetime import datetime
from app.services.vonage_service import initiate_outbound_call

logger = logging.getLogger(__name__)

class CallScheduler:
    """
    Manages scheduled outbound calls.
    Uses 'schedule' library for job orchestration in a background thread.
    """
    
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None

    def schedule_call(self, to_number: str, time_str: str, reason: str = None, notes: str = None, voice_id: str = None) -> str:
        """
        Schedule a call at a specific time (HH:MM).
        
        Args:
            to_number: Destination phone number
            time_str: 24h format "HH:MM"
            reason: Optional reason for call
            notes: Optional additional notes
            voice_id: Specific voice twin to use
        """
        job_id = f"call_{to_number}_{time_str}_{int(time.time())}"
        
        def job():
            logger.info(f"Executing scheduled call to {to_number} (Reason: {reason}, Voice: {voice_id})")
            try:
                initiate_outbound_call(to_number, reason=reason, notes=notes, voice_id=voice_id)
                return schedule.CancelJob
            except Exception as e:
                logger.error(f"Failed to execute scheduled call: {e}")

        schedule.every().day.at(time_str).do(job).tag(job_id)


        logger.info(f"Scheduled call to {to_number} for {time_str}")
        return job_id

    def _run_loop(self):
        """Internal loop for checking pending jobs."""
        logger.info("Scheduler loop started.")
        count = 0
        while not self._stop_event.is_set():
            count += 1
            if count % 30 == 0:
                logger.info(f"Scheduler heartbeat. Current time: {time.strftime('%H:%M:%S')}")
            schedule.run_pending()
            time.sleep(1)

    def start(self):
        """Start the background scheduler thread."""
        if self._thread and self._thread.is_alive():
            return
            
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("Background call scheduler started.")


    def stop(self):
        """Stop the background scheduler thread."""
        self._stop_event.set()
        if self._thread:
            self._thread.join()
