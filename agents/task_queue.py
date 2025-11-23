"""Simple in-memory task queue with a background worker.

This is a minimal implementation suitable for CI and local development.
It exposes `enqueue(task)` and `start(worker_callable)` to begin
processing tasks. The worker_callable should be an async callable that
accepts the task dict.
"""
import asyncio
from typing import Any, Callable, Optional


class TaskQueue:
    def __init__(self):
        self._queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
        self._running = False

    async def _worker(self, worker_callable: Callable[[dict], Any]):
        while self._running:
            task = await self._queue.get()
            try:
                await worker_callable(task)
            except Exception:
                # swallow errors here; worker_callable should log
                pass
            finally:
                self._queue.task_done()

    def enqueue(self, task: dict):
        self._queue.put_nowait(task)

    def start(self, worker_callable: Callable[[dict], Any]):
        if self._running:
            return
        loop = asyncio.get_event_loop()
        self._running = True
        self._worker_task = loop.create_task(self._worker(worker_callable))

    async def stop(self):
        self._running = False
        if self._worker_task:
            self._worker_task.cancel()
            try:
                await self._worker_task
            except Exception:
                pass
