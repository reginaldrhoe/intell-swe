"""Small Celery worker helper that calls local MCP handle_task.

This module provides a `process_local_task` function which the Celery task
in `celery_queue.py` calls. It imports the `mcp` FastAPI module's MCP
instance (if available) or constructs a local MasterControlPanel.
"""
def process_local_task(task_payload: dict):
    try:
        # Try to import the running MCP module and call its MCP instance
        from mcp import mcp as running_mcp  # type: ignore
        coro = running_mcp.handle_task(task_payload)
        import asyncio
        asyncio.run(coro)
    except Exception:
        # Fallback: import local agents MasterControlPanel
        try:
            from agents.agents import MasterControlPanel
            m = MasterControlPanel()
            import asyncio
            asyncio.run(m.handle_task(task_payload))
        except Exception:
            # nothing else we can do in worker
            raise
