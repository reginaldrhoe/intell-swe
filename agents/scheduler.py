"""Lightweight asyncio-based scheduler for periodic tasks.

If APScheduler is available it can be integrated later; for now this
provides a simple recurring job runner suitable for summaries and
maintenance tasks.
"""
import asyncio
from typing import Callable, Optional


class SimpleScheduler:
    def __init__(self):
        self._tasks = []

    def add_job(self, coro_func: Callable[[], None], interval_seconds: int):
        """Schedule `coro_func` to run every `interval_seconds` seconds."""
        task = asyncio.create_task(self._run_periodic(coro_func, interval_seconds))
        self._tasks.append(task)

    async def _run_periodic(self, coro_func: Callable[[], None], interval: int):
        while True:
            try:
                await coro_func()
            except Exception:
                pass
            await asyncio.sleep(interval)

    async def stop_all(self):
        for t in self._tasks:
            t.cancel()
        for t in self._tasks:
            try:
                await t
            except Exception:
                pass
