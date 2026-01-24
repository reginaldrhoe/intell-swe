
import asyncio
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Callable, Optional

# Try to import models and db, assuming they are available in the python path
try:
    from mcp.db import SessionLocal
    from mcp.models import ScheduledTask
except ImportError:
    SessionLocal = None
    ScheduledTask = None

class DatabaseScheduler:
    def __init__(self, mcp_instance=None):
        self._stop_event = asyncio.Event()
        self._task = None
        self.mcp = mcp_instance
        self.logger = logging.getLogger(__name__)

    def start(self):
        """Start the scheduler polling loop."""
        if self._task is None:
            self._task = asyncio.create_task(self._poll_loop())
            self.logger.info("DatabaseScheduler started.")

    async def stop(self):
        """Stop the scheduler."""
        if self._task:
            self._stop_event.set()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
            self.logger.info("DatabaseScheduler stopped.")

    async def _poll_loop(self):
        """Main polling loop."""
        while not self._stop_event.is_set():
            try:
                await self._check_and_run_tasks()
            except Exception as e:
                self.logger.exception("Error in scheduler poll loop: %s", e)
            
            # Poll every 60 seconds (or configurable)
            try:
                await asyncio.wait_for(self._stop_event.wait(), timeout=60)
            except asyncio.TimeoutError:
                pass # timeout reached, loop again

    async def _check_and_run_tasks(self):
        if not SessionLocal or not ScheduledTask:
            self.logger.warning("Database models not available, skipping schedule check.")
            return

        db = SessionLocal()
        try:
            now = datetime.utcnow()
            # Find due tasks
            due_tasks = db.query(ScheduledTask).filter(
                ScheduledTask.is_active == True,
                (ScheduledTask.next_run_at <= now) | (ScheduledTask.next_run_at == None)
            ).all()

            for task in due_tasks:
                await self._process_task(db, task, now)
        finally:
            db.close()

    async def _process_task(self, db, task_record, now):
        self.logger.info("Processing scheduled task: %s (ID: %s)", task_record.name, task_record.id)
        
        # 1. Dispatch the task
        if self.mcp:
            try:
                payload = json.loads(task_record.task_payload)
                # Ensure it's treated as a background task if possible, 
                # though mcp.handle_task is async so we await it here.
                # We spin it off as a separate task to not block the scheduler loop?
                asyncio.create_task(self.mcp.handle_task(payload))
            except Exception as e:
                self.logger.error("Failed to dispatch task %s: %s", task_record.id, e)

        # 2. Update next_run_at
        task_record.last_run_at = now
        
        if task_record.schedule_type == 'interval':
            try:
                seconds = int(task_record.schedule_value)
                task_record.next_run_at = now + timedelta(seconds=seconds)
            except ValueError:
                self.logger.error("Invalid interval value for task %s: %s", task_record.id, task_record.schedule_value)
                task_record.is_active = False # Disable invalid task
        elif task_record.schedule_type == 'cron':
            # Basic cron support requires croniter; if missing, disable task
            try:
                from croniter import croniter
                iter = croniter(task_record.schedule_value, now)
                task_record.next_run_at = iter.get_next(datetime)
            except ImportError:
                self.logger.error("croniter not installed, cannot process cron task %s", task_record.id)
                task_record.is_active = False
            except Exception as e:
                self.logger.error("Error calculating cron next run for task %s: %s", task_record.id, e)
                task_record.is_active = False
        
        db.commit()

# Alias for backward compatibility if needed, though we should update mcp.py to use DatabaseScheduler
SimpleScheduler = DatabaseScheduler
