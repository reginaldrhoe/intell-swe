"""Optional Celery-backed queue wrapper with Redis broker.

If `CELERY_BROKER_URL` is set in the environment and `celery` is installed,
this module exposes `get_queue()` which returns an object with `enqueue(task)`
signature. If Celery is not available or broker not configured, callers can
fall back to the in-memory `TaskQueue`.
"""
import os
from typing import Optional, Any

try:
    from celery import Celery
    from celery.utils.log import get_task_logger
except Exception:
    Celery = None
    get_task_logger = None


class CeleryQueueWrapper:
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        self.app = Celery("rag_poc", broker=broker_url)
        # default JSON serializer
        self.app.conf.task_serializer = "json"
        self.app.conf.result_serializer = "json"
        self.app.conf.accept_content = ["json"]
        self.logger = get_task_logger(__name__) if get_task_logger else None

        @self.app.task(bind=True, max_retries=3, default_retry_delay=10)
        def _process_task(self_task, task_payload):
            # This Celery task will import the MCP and call handle_task.
            try:
                # import lazily to avoid circular imports at module load
                from agents import celery_local_worker as worker
                worker.process_local_task(task_payload)
            except Exception as exc:
                # retry on exception
                raise self_task.retry(exc=exc)

        self._task = _process_task

    def enqueue(self, task: dict):
        # send task to Celery worker with retry policy
        self._task.apply_async(args=[task])


def get_queue():
    broker = os.getenv("CELERY_BROKER_URL")
    if broker and Celery is not None:
        return CeleryQueueWrapper(broker)
    return None
