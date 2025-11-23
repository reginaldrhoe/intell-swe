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

# Module-level Celery app for the worker command to import (celery -A agents.celery_queue)
celery = None
if Celery is not None and os.getenv("CELERY_BROKER_URL"):
    celery = Celery("rag_poc", broker=os.getenv("CELERY_BROKER_URL"))
    # default JSON serializer
    celery.conf.task_serializer = "json"
    celery.conf.result_serializer = "json"
    celery.conf.accept_content = ["json"]

    @celery.task(bind=True, max_retries=3, default_retry_delay=10)
    def process_task(self_task, task_payload):
        try:
            from agents import celery_local_worker as worker
            worker.process_local_task(task_payload)
        except Exception as exc:
            # retry on exception
            raise self_task.retry(exc=exc)


class CeleryQueueWrapper:
    def __init__(self, broker_url: str):
        self.broker_url = broker_url
        # Use existing module-level celery if present
        if celery is not None:
            self.app = celery
        else:
            self.app = Celery("rag_poc", broker=broker_url)
            self.app.conf.task_serializer = "json"
            self.app.conf.result_serializer = "json"
            self.app.conf.accept_content = ["json"]
        self.logger = get_task_logger(__name__) if get_task_logger else None

    def enqueue(self, task: dict):
        # send task to Celery worker with retry policy
        if celery is not None:
            process_task.apply_async(args=[task])
        else:
            # fallback to creating a temporary task
            self.app.send_task("agents.celery_queue.process_task", args=[task])


def get_queue():
    broker = os.getenv("CELERY_BROKER_URL")
    if broker and Celery is not None:
        return CeleryQueueWrapper(broker)
    return None
