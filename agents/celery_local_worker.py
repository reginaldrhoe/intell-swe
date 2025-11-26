"""Small Celery worker helper that calls local MCP handle_task.

This module provides a `process_local_task` function which the Celery task
in `celery_queue.py` calls. It imports the `mcp` FastAPI module's MCP
instance (if available) or constructs a local MasterControlPanel.
"""
import logging
def process_local_task(task_payload: dict):
    # Try to coordinate across processes using a redis lock if available so
    # Celery workers don't step on a concurrently-running API instance.
    lock_client = None
    lock_token = None
    lock_acquired = False
    try:
        task_id = task_payload.get('id') if isinstance(task_payload, dict) else None
        if task_id is not None:
            try:
                from os import getenv
                redis_url = getenv('REDIS_URL') or getenv('CELERY_BROKER_URL')
                if redis_url:
                    # import helper lazily to avoid hard dependency when not needed
                        try:
                            from mcp.redis_lock import acquire_lock_sync, release_lock_sync
                            lock_key = f"task:{int(task_id)}:lock"
                            logging.debug("Worker attempting sync redis lock for %s", lock_key)
                            lock_client, lock_token = acquire_lock_sync(redis_url, lock_key, int(getenv('TASK_LOCK_TTL', '3600')))
                            if lock_token is None:
                                # someone else holds the lock — skip processing
                                logging.info("Worker found lock held for %s; skipping", lock_key)
                                return
                            lock_acquired = True
                            logging.info("Worker acquired lock for %s", lock_key)
                    except Exception:
                        # fall back to DB-only protection if redis helper not available
                        lock_client = None
                        lock_token = None
                        lock_acquired = False
            except Exception:
                pass

    except Exception:
        # continue; we'll attempt to run task without distributed lock
        lock_client = None
        lock_token = None
        lock_acquired = False

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
            results = asyncio.run(m.handle_task(task_payload))
            # Persist results to DB so the API/SSE consumers can observe activity
            try:
                from mcp.db import SessionLocal
                from mcp import models
                db = SessionLocal()
                try:
                    for agent_name, content in (results or {}).items():
                        try:
                            agent_obj = None
                            try:
                                agent_obj = db.query(models.Agent).filter(models.Agent.name == agent_name).first()
                            except Exception:
                                agent_obj = None
                            agent_id = agent_obj.id if agent_obj else None
                            a = models.Activity(task_id=task_payload.get('id'), agent_id=agent_id, content=str(content))
                            db.add(a)
                        except Exception:
                            # ignore per-activity persistence failures
                            pass
                    # mark task done
                    try:
                        t = db.query(models.Task).filter(models.Task.id == int(task_payload.get('id'))).first()
                        if t is not None:
                            t.status = 'done'
                            db.add(t)
                    except Exception:
                        pass
                    try:
                        db.commit()
                    except Exception:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                finally:
                    try:
                        db.close()
                    except Exception:
                        pass
            except Exception:
                # best-effort; do not let DB persistence break worker execution
                pass
        except Exception:
            # nothing else we can do in worker
            raise
    finally:
        # release the lock if we acquired it
        try:
            if lock_acquired and lock_client is not None and lock_token is not None:
                try:
                    from mcp.redis_lock import release_lock_sync
                    logging.info("Worker releasing lock for task:%s", int(task_payload.get('id')))
                    release_lock_sync(lock_client, f"task:{int(task_payload.get('id'))}:lock", lock_token)
                    logging.debug("Worker released lock for task:%s", int(task_payload.get('id')))
                except Exception:
                    logging.exception("Worker failed to release lock for task:%s", int(task_payload.get('id')))
        except Exception:
            pass
