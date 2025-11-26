from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
from fastapi.responses import StreamingResponse
import asyncio
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import Dict, Any
from pathlib import Path
from agents.agents import MasterControlPanel
from agents.task_queue import TaskQueue
from agents.scheduler import SimpleScheduler
from mcp.auth import check_admin_token
from mcp.metrics import TASKS_ENQUEUED, AGENT_RUNS, INGEST_COUNTER, metrics_response
from mcp.api import router as api_router
from mcp.oauth import router as oauth_router
from mcp.db import SessionLocal
from mcp import models
from sqlalchemy.orm import Session
import logging
import threading
import subprocess
import sys
from datetime import datetime
from mcp.redis_lock import acquire_lock_async, release_lock_async, acquire_lock_sync, release_lock_sync

app = FastAPI()
# Configure CORS for local development. You can override origins with the
# environment variable `CORS_ALLOW_ORIGINS` (comma-separated list).
_cors_env = os.getenv('CORS_ALLOW_ORIGINS')
if _cors_env:
    _origins = [o.strip() for o in _cors_env.split(',') if o.strip()]
else:
    _origins = [
        'http://localhost:5173',
        'http://localhost:3000',
        'http://localhost:8000',
    ]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(api_router)
app.include_router(oauth_router)

# Optional in-app OpenAI mock: when `IN_APP_OPENAI_MOCK` is truthy, mount
# the mock OpenAI app so the mcp server can serve OpenAI-compatible
# endpoints at `/openai-mock/v1/...`.
try:
    if os.getenv('IN_APP_OPENAI_MOCK'):
        try:
            from mcp.openai_mock import app as _openai_mock_app
            app.mount('/openai-mock', _openai_mock_app)
        except Exception:
            # don't fail startup if mock import fails
            logging.exception('Failed to mount in-app OpenAI mock')
except Exception:
    pass

# If configured, set OpenAI API base to point to in-app mock so OpenAI client
# calls are redirected without modifying other code paths. This helps tests
# and local dev when `IN_APP_OPENAI_MOCK` is enabled.
try:
    if os.getenv('IN_APP_OPENAI_MOCK'):
        # prefer explicit env override if provided
        base = os.getenv('IN_APP_OPENAI_MOCK_BASE') or 'http://localhost:8001/openai-mock'
        os.environ.setdefault('OPENAI_API_BASE', base)
        # clear OPENAI_API_KEY unless explicitly set to avoid accidental real calls
        if not os.getenv('OPENAI_API_KEY'):
            os.environ.setdefault('OPENAI_API_KEY', '')
        logging.info('IN_APP_OPENAI_MOCK enabled; set OPENAI_API_BASE=%s', base)
except Exception:
    pass

# Instantiate the MasterControlPanel later (after publisher is available).
mcp = None

# Task queue used by webhook endpoints. We will prefer a Celery-backed
# queue when `CELERY_BROKER_URL` is configured and Celery is installed.
task_queue = None

# Simple scheduler for periodic jobs
scheduler = SimpleScheduler()

# In-memory pubsub for server-sent events (SSE) per task id.
# Maps task_id -> list of asyncio.Queue instances to push events to connected clients.
TASK_EVENT_QUEUES: dict[int, list[asyncio.Queue]] = {}

# Optional redis async client for cross-process pubsub
redis_client = None
try:
    import redis.asyncio as aioredis  # type: ignore
except Exception:
    aioredis = None

def _register_task_queue(task_id: int, q: asyncio.Queue):
    lst = TASK_EVENT_QUEUES.get(task_id)
    if lst is None:
        TASK_EVENT_QUEUES[task_id] = [q]
    else:
        lst.append(q)

def _unregister_task_queue(task_id: int, q: asyncio.Queue):
    lst = TASK_EVENT_QUEUES.get(task_id)
    if not lst:
        return
    try:
        lst.remove(q)
    except ValueError:
        pass
    if not lst:
        TASK_EVENT_QUEUES.pop(task_id, None)

async def _publish_task_event(task_id: int, event: dict):
    # publish to redis channel if available
    try:
        if aioredis is not None and redis_client is not None:
            try:
                ch = f"task:{task_id}"
                await redis_client.publish(ch, json.dumps(event))
            except Exception:
                pass
    except Exception:
        pass

    lst = TASK_EVENT_QUEUES.get(task_id) or []
    # make shallow copy to avoid mutation during iteration
    for q in list(lst):
        try:
            # don't await put directly to avoid blocking
            await q.put(event)
        except Exception:
            # ignore per-queue failures
            pass

    # Persist certain event types to the database using a session-per-event
    try:
        async def _persist_event():
            try:
                def _sync_persist():
                    db = SessionLocal()
                    try:
                        etype = event.get("type")
                        if etype == "activity":
                            # persist Activity row
                            agent_name = event.get("agent")
                            try:
                                agent_obj = db.query(models.Agent).filter(models.Agent.name == agent_name).first() if agent_name else None
                                agent_id = agent_obj.id if agent_obj else None
                            except Exception:
                                agent_id = None
                            a = models.Activity(task_id=task_id, agent_id=agent_id, content=str(event.get("content")))
                            db.add(a)
                            db.commit()
                        elif etype == "status":
                            # update task status field
                            try:
                                t = db.query(models.Task).filter(models.Task.id == int(task_id)).first()
                                if t is not None:
                                    t.status = event.get("status")
                                    db.add(t)
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

                # run the sync DB work in a thread to avoid blocking the event loop
                import asyncio as _asyncio
                _asyncio.get_running_loop().run_in_executor(None, _sync_persist)
            except Exception:
                pass

        # kick off persistence but don't await so publishing remains fast
        asyncio.create_task(_persist_event())
    except Exception:
        pass


@app.on_event("startup")
async def _startup():
    # start the task queue worker; worker delegates to mcp.handle_task
    def _worker_callable(task):
        # Wrap the async call to mcp.handle_task
        return mcp.handle_task(task)

    # Try to use Celery-backed queue if available; otherwise start in-memory worker
    try:
        # import lazily so Celery is optional at runtime
        from agents.celery_queue import get_queue

        q = get_queue()
    except Exception:
        q = None

    global task_queue
    if q is not None:
        # Celery is configured and available — use its wrapper (no .start required)
        task_queue = q
    else:
        # Use the in-memory TaskQueue for local/dev
        task_queue = TaskQueue()
        task_queue.start(_worker_callable)

    # Example scheduled job: daily summary (runs every 24h)
    async def _daily_summary():
        # placeholder: in future generate a summary report
        return

    scheduler.add_job(_daily_summary, interval_seconds=24 * 3600)


    # If aioredis is available and a redis URL is configured, create a redis client
    global redis_client, mcp
    try:
        # Prefer explicit REDIS_URL / CELERY_BROKER_URL but default to docker-compose service
        redis_url = os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL') or 'redis://redis:6379/0'
        if aioredis is not None and redis_url:
            try:
                redis_client = aioredis.from_url(redis_url, decode_responses=True)
            except Exception:
                redis_client = None
    except Exception:
        redis_client = None

    # instantiate MasterControlPanel with publisher callback so agents can publish events
    try:
        if mcp is None:
            mcp = MasterControlPanel(publisher=_publish_task_event)
    except Exception:
        # fallback to no publisher
        try:
            mcp = MasterControlPanel()
        except Exception:
            mcp = None


@app.on_event("shutdown")
async def _shutdown():
    # If we are using the in-memory TaskQueue, stop its worker. Celery-backed
    # queues do not expose an async stop and are managed externally.
    try:
        if isinstance(task_queue, TaskQueue):
            await task_queue.stop()
    except Exception:
        pass
    try:
        await scheduler.stop_all()
    except Exception:
        pass

# Optional imports for embeddings and qdrant client (used by the similarity endpoint)
OpenAIEmbeddings = None
try:
    from langchain_openai import OpenAIEmbeddings  # type: ignore
except Exception:
    try:
        from langchain.embeddings import OpenAIEmbeddings  # type: ignore
    except Exception:
        OpenAIEmbeddings = None

try:
    from qdrant_client import QdrantClient  # type: ignore
except Exception:
    QdrantClient = None

# Prefer the OpenAI v1 client when available
try:
    from openai import OpenAI as OpenAIClient  # type: ignore
except Exception:
    OpenAIClient = None


def deterministic_embedding(text: str, dim: int = 1536):
    import hashlib
    import numpy as _np

    h = hashlib.sha256(text.encode("utf-8")).digest()
    vals = []
    i = 0
    while len(vals) < dim:
        b = h[i % len(h)]
        vals.append((b / 255.0) * 2.0 - 1.0)
        i += 1
    vec = _np.array(vals[:dim], dtype=float)
    norm = _np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def get_embedding(text: str):
    # If in-app mock is configured, call the mock embeddings endpoint directly
    try:
        if os.getenv('IN_APP_OPENAI_MOCK'):
            try:
                import requests as _requests
                base = os.getenv('IN_APP_OPENAI_MOCK_BASE') or os.getenv('OPENAI_API_BASE') or 'http://localhost:8001/openai-mock'
                url = base.rstrip('/') + '/v1/embeddings'
                payload = {'input': text, 'model': 'text-embedding-mock'}
                r = _requests.post(url, json=payload, timeout=10)
                r.raise_for_status()
                j = r.json()
                if isinstance(j, dict) and j.get('data') and isinstance(j['data'], list):
                    return j['data'][0].get('embedding')
            except Exception:
                logging.exception('Failed to call in-app OpenAI mock embeddings; falling back')
    except Exception:
        pass
    # 1) If an OpenAI API key is present prefer the OpenAI v1 client (higher-fidelity)
    if os.getenv("OPENAI_API_KEY") and OpenAIClient is not None:
        try:
            client = OpenAIClient()
            resp = client.embeddings.create(model="text-embedding-3-small", input=text)
            # resp.data[0].embedding is the vector
            return resp.data[0].embedding
        except Exception:
            # fall through to other options
            pass

    # 2) Try LangChain's OpenAIEmbeddings wrapper if available
    if OpenAIEmbeddings is not None:
        try:
            emb = OpenAIEmbeddings()  # type: ignore
            try:
                return emb.embed_documents([text])[0]
            except Exception:
                return emb.embed_query(text)
        except Exception:
            pass

    # 3) Deterministic fallback — use 1536 to match common OpenAI embedding size
    return deterministic_embedding(text, dim=1536)


@app.post("/run-agents")
async def run_agents(task: dict):
    """Accept a task JSON and dispatch to the Agent framework.

    Example request body:
    {
        "title": "Fix failing tests",
        "description": "Integration tests failing on branch X",
        "files": ["pipeline.py"]
    }
    """
    # Verbose debug: log incoming payload and mark entry so we can trace
    # whether the lock path is being exercised in production runs.
    try:
        logging.info("RUN_AGENTS_DBG: received task payload: %s", json.dumps(task))
    except Exception:
        logging.info("RUN_AGENTS_DBG: received task (non-serializable)")
    # Sentinel: write a small line to /tmp so tests can deterministically detect handler entry
    try:
        try:
            tid = task.get('id') if isinstance(task, dict) else 'N/A'
        except Exception:
            tid = 'N/A'
        with open('/tmp/run_agents_entered.log', 'a', encoding='utf-8') as _fh:
            _fh.write(f"{datetime.utcnow().isoformat()} RUN_AGENTS_ENTERED id={tid}\n")
    except Exception:
        logging.exception("RUN_AGENTS_DBG: failed to write run_agents sentinel")

    # Quick up-front Redis lock existence check: if an external process already
    # holds the lock for this task, return 409 immediately. This avoids doing
    # DB lookups when a worker or another API instance already owns the task.
    try:
        if isinstance(task, dict) and task.get('id') is not None:
            task_id_quick = int(task.get('id'))
            try:
                redis_url = os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL') or 'redis://redis:6379/0'
                key = f"task:{task_id_quick}:lock"
                logging.info("RUN_AGENTS_DBG: up-front check for key=%s using redis_url=%s aioredis=%s redis_client=%s", key, redis_url, bool(aioredis), bool(redis_client))
                # prefer existing async client
                if aioredis is not None and redis_client is not None:
                    try:
                        v = await redis_client.get(key)
                        logging.info("RUN_AGENTS_DBG: async redis get for %s -> %s", key, str(v))
                        if v:
                            logging.info("Up-front check: lock present for %s, rejecting run", key)
                            try:
                                with open('/tmp/run_agents_lock_conflict.log', 'a', encoding='utf-8') as _cf:
                                    _cf.write(f"{datetime.utcnow().isoformat()} UPFRONT_CONFLICT key={key} method=async value={str(v)}\n")
                            except Exception:
                                logging.exception('RUN_AGENTS_DBG: failed writing upfront conflict sentinel')
                            raise HTTPException(status_code=409, detail=f"Task {task_id_quick} is already running")
                    except Exception:
                        logging.exception("RUN_AGENTS_DBG: Up-front async redis check failed for %s", key)
                else:
                    # try a short sync get via executor (redis-py)
                    if redis_url:
                        try:
                            import redis as _redis
                            def _get():
                                c = _redis.from_url(redis_url, decode_responses=True)
                                return c.get(key)
                            val = await asyncio.get_running_loop().run_in_executor(None, _get)
                            logging.info("RUN_AGENTS_DBG: sync redis get for %s -> %s", key, str(val))
                            if val:
                                logging.info("Up-front check: lock present for %s (sync), rejecting run", key)
                                try:
                                    with open('/tmp/run_agents_lock_conflict.log', 'a', encoding='utf-8') as _cf:
                                        _cf.write(f"{datetime.utcnow().isoformat()} UPFRONT_CONFLICT key={key} method=sync value={str(val)}\n")
                                except Exception:
                                    logging.exception('RUN_AGENTS_DBG: failed writing upfront sync conflict sentinel')
                                raise HTTPException(status_code=409, detail=f"Task {task_id_quick} is already running")
                        except HTTPException:
                            raise
                        except Exception:
                            logging.exception("RUN_AGENTS_DBG: Up-front sync redis check failed for %s", key)
            except HTTPException:
                # propagate conflict
                raise
            except Exception:
                # non-fatal: proceed to DB-level checks
                logging.exception("RUN_AGENTS_DBG: Up-front redis existence check encountered an error; continuing with DB fallback")

    except Exception:
        # keep behavior conservative: fall through to existing logic on unexpected errors
        pass

    # If a task id was provided (from /api/tasks creation), persist status and activities
    db: Session = None
    task_record = None
    lock_acquired = False
    lock_token = None
    lock_client = None

    try:
        if isinstance(task, dict) and task.get('id') is not None:
            db = SessionLocal()
            try:
                task_record = db.query(models.Task).filter(models.Task.id == int(task.get('id'))).first()
                if task_record:
                    # Attempt distributed lock first (if redis is configured)
                    try:
                        redis_url = os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL') or 'redis://redis:6379/0'
                        lock_key = f"task:{task_record.id}:lock"
                        lock_ttl = int(os.getenv('TASK_LOCK_TTL', '3600'))
                        logging.info("RUN_AGENTS_DBG: attempting lock acquisition for %s using redis_url=%s aioredis=%s redis_client=%s",
                                     lock_key, redis_url, bool(aioredis), bool(redis_client))

                        # Prefer module-level async client
                        if aioredis is not None and redis_client is not None:
                            logging.info("RUN_AGENTS_DBG: Attempting async redis lock for %s via module client", lock_key)
                            lock_token = await acquire_lock_async(redis_client, lock_key, lock_ttl)
                            if lock_token is None:
                                logging.info("RUN_AGENTS_DBG: Redis lock for %s already held (async client)", lock_key)
                                try:
                                    with open('/tmp/run_agents_lock_conflict.log', 'a', encoding='utf-8') as _cf:
                                        _cf.write(f"{datetime.utcnow().isoformat()} LOCK_CONFLICT key={lock_key} method=async\n")
                                except Exception:
                                    logging.exception('RUN_AGENTS_DBG: failed writing async conflict sentinel')
                                try:
                                    db.close()
                                except Exception:
                                    pass
                                raise HTTPException(status_code=409, detail=f"Task {task_record.id} is already running")
                            # success
                            try:
                                with open('/tmp/run_agents_lock_acquired.log', 'a', encoding='utf-8') as _af:
                                    _af.write(f"{datetime.utcnow().isoformat()} LOCK_ACQUIRED key={lock_key} method=async token_len={len(lock_token) if lock_token else 0}\n")
                            except Exception:
                                logging.exception('RUN_AGENTS_DBG: failed writing async acquired sentinel')
                            lock_acquired = True
                            lock_client = redis_client

                        else:
                            # Try a sync redis client via executor
                            if redis_url:
                                try:
                                    import asyncio as _asyncio

                                    def _acquire_sync():
                                        return acquire_lock_sync(redis_url, lock_key, lock_ttl)

                                    client_token = await _asyncio.get_running_loop().run_in_executor(None, _acquire_sync)
                                    if client_token and client_token[1] is not None:
                                        lock_client, lock_token = client_token
                                        lock_acquired = True
                                        try:
                                            with open('/tmp/run_agents_lock_acquired.log', 'a', encoding='utf-8') as _af:
                                                _af.write(f"{datetime.utcnow().isoformat()} LOCK_ACQUIRED key={lock_key} method=sync token_len={len(lock_token) if lock_token else 0}\n")
                                        except Exception:
                                            logging.exception('RUN_AGENTS_DBG: failed writing sync acquired sentinel')
                                    else:
                                        try:
                                            with open('/tmp/run_agents_lock_conflict.log', 'a', encoding='utf-8') as _cf:
                                                _cf.write(f"{datetime.utcnow().isoformat()} LOCK_CONFLICT key={lock_key} method=sync\n")
                                        except Exception:
                                            logging.exception('RUN_AGENTS_DBG: failed writing sync conflict sentinel')
                                        try:
                                            db.close()
                                        except Exception:
                                            pass
                                        raise HTTPException(status_code=409, detail=f"Task {task_record.id} is already running")
                                except HTTPException:
                                    raise
                                except Exception:
                                    logging.exception("Sync redis lock attempt failed; falling back to DB-only duplicate protection")

                    except HTTPException:
                        raise
                    except Exception:
                        logging.exception("Redis lock acquisition failed; falling back to DB-only duplicate protection")

                    # If we didn't get a redis lock, perform an atomic DB update
                    if not lock_acquired:
                        try:
                            rows = db.query(models.Task).filter(models.Task.id == int(task_record.id), models.Task.status != 'running').update({"status": "running"}, synchronize_session=False)
                            db.commit()
                            if not rows:
                                try:
                                    db.close()
                                except Exception:
                                    pass
                                raise HTTPException(status_code=409, detail=f"Task {task_record.id} is already running")
                        except HTTPException:
                            raise
                        except Exception:
                            try:
                                db.rollback()
                            except Exception:
                                pass
                            try:
                                task_record.status = 'running'
                                db.add(task_record)
                                db.commit()
                            except Exception:
                                try:
                                    db.rollback()
                                except Exception:
                                    pass
                    else:
                        try:
                            task_record.status = 'running'
                            db.add(task_record)
                            db.commit()
                        except Exception:
                            try:
                                db.rollback()
                            except Exception:
                                pass

                    try:
                        asyncio.create_task(_publish_task_event(task_record.id, {"type": "status", "status": "running"}))
                    except Exception:
                        pass
                    
                    # Enrich task dict with database fields for agent processing
                    task["description"] = task_record.description or ""
                    task["id"] = task_record.id
                    task["title"] = task_record.title or task.get("title", "")
                    logging.info(f"RUN_AGENTS_DBG: Enriched task dict with description (len={len(task.get('description',''))}), title={task.get('title')}")
            except Exception:
                try:
                    db.rollback()
                except Exception:
                    pass
    except HTTPException:
        raise
    except Exception:
        try:
            if db:
                db.rollback()
        except Exception:
            pass

    try:
        results = await mcp.handle_task(task)
        return {"results": results}
    except Exception as e:
        try:
            if task_record is not None:
                try:
                    task_record.status = 'failed'
                    db.add(task_record)
                    db.commit()
                except Exception:
                    try:
                        db.rollback()
                    except Exception:
                        pass
                try:
                    await _publish_task_event(task_record.id, {"type": "status", "status": "failed"})
                except Exception:
                    pass
        except Exception:
            pass
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # release redis lock if we acquired it
        try:
            if lock_acquired and lock_client is not None and lock_token is not None:
                try:
                    logging.info("Releasing redis lock for task:%s", task_record.id if task_record else 'N/A')
                    await release_lock_async(lock_client, f"task:{task_record.id}:lock" if task_record else None, lock_token)
                    logging.debug("Released redis lock for task:%s", task_record.id if task_record else 'N/A')
                except Exception:
                    logging.exception("Failed to release redis lock for task:%s", task_record.id if task_record else 'N/A')
        except Exception:
            pass
        try:
            if db:
                db.close()
        except Exception:
            pass


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/similarity-search")
async def similarity_search(body: dict):
    """Run a similarity search against Qdrant.

    Request body example:
    {
      "query": "search text",
      "k": 3,
      "collection": "rag-poc"
    }
    """
    query = body.get("query")
    if not query:
        raise HTTPException(status_code=400, detail="Missing 'query' in request body")
    k = int(body.get("k", 3))
    collection = body.get("collection")

    # If collection not provided, try to read from persisted RAG config
    try:
        cfg = load_rag_config()
        if collection is None:
            collection = cfg.get("collection", "rag-poc")
    except Exception:
        collection = collection or "rag-poc"

    if QdrantClient is None:
        raise HTTPException(status_code=500, detail="qdrant-client is not installed in the environment")

    q_vector = get_embedding(query)

    # Determine Qdrant host (when running inside container use service name)
    qdrant_url = os.getenv("QDRANT_URL") or "http://qdrant:6333"

    try:
        client = QdrantClient(url=qdrant_url)
        resp = client.query_points(collection_name=collection, query=q_vector, limit=k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Qdrant query failed: {e}")

    # Normalize results
    hits = []
    if hasattr(resp, "result"):
        items = resp.result
    else:
        items = getattr(resp, "hits", getattr(resp, "points", []))

    for item in items:
        payload = None
        if hasattr(item, "payload"):
            payload = item.payload
        elif isinstance(item, dict):
            payload = item.get("payload") or item.get("document")
        else:
            payload = getattr(item, "point", None)

        if isinstance(payload, dict):
            text = payload.get("text") or payload.get("page_content") or str(payload)
        else:
            text = str(payload)
        # Extract score/metadata if present
        score = None
        source = None
        try:
            if hasattr(item, "score"):
                score = float(item.score)
            elif isinstance(item, dict):
                score = item.get("score") or item.get("payload", {}).get("score")
        except Exception:
            score = None

        if isinstance(payload, dict):
            # look for common source/metadata fields
            source = payload.get("source") or payload.get("metadata") or payload.get("source_id")

        hit = {"text": text}
        if score is not None:
            hit["score"] = score
        if source is not None:
            hit["source"] = source

        hits.append(hit)

    return {"query": query, "results": hits}


# --- RAG selection persistence and API ---
RAG_CONFIG_PATH = Path(__file__).resolve().parent.parent / "agents" / "rag_config.json"


def load_rag_config() -> Dict[str, Any]:
    try:
        if not RAG_CONFIG_PATH.exists():
            return {"repos": [], "collection": "rag-poc"}
        with open(RAG_CONFIG_PATH, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
            # normalize shape for backward compatibility
            if "collection" not in cfg:
                cfg.setdefault("collection", "rag-poc")
            if "repos" not in cfg:
                # support old `repo` key or missing repos
                if cfg.get("repo"):
                    cfg["repos"] = [cfg.get("repo")]
                    cfg.pop("repo", None)
                else:
                    cfg["repos"] = []
            # normalize each repo entry to an object
            out_repos = []
            for r in cfg.get("repos", []):
                if isinstance(r, str):
                    out_repos.append({"url": r, "auto_ingest": True})
                elif isinstance(r, dict):
                    # ensure required keys and defaults
                    o = dict(r)
                    o.setdefault("url", "")
                    o.setdefault("auto_ingest", True)
                    # optional fields: collection, branches
                    if "branches" in o and o.get("branches") is None:
                        o.pop("branches", None)
                    out_repos.append(o)
            cfg["repos"] = out_repos
            return cfg
    except Exception:
        return {"repos": [], "collection": "rag-poc"}


def save_rag_config(cfg: Dict[str, Any]):
    try:
        RAG_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        # normalize: ensure repos is a list
        if "repos" not in cfg:
            cfg["repos"] = [] if cfg.get("repo") is None else [cfg.get("repo")]
            cfg.pop("repo", None)
        with open(RAG_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except Exception as e:
        raise


# Background ingest helper: spawn a daemon thread that runs the ingest script
PROJECT_ROOT = Path(__file__).resolve().parent.parent
_logger = logging.getLogger(__name__)

def _spawn_ingest_for_repo(repo_url: str, collection: str | None = None, ref: str | None = None, sha: str | None = None):
    """Spawn a background thread to run `scripts/ingest_repo.py` for the given repo_url.

    Accepts an optional Git `ref` (e.g. `refs/heads/feature`) and/or `sha` to
    ensure the ingest indexes the pushed branch/commit. These are forwarded
    as `--branch` / `--commit` CLI flags to `scripts/ingest_repo.py`.
    
    Queries database for last indexed commit to enable incremental diff-based updates.
    """
    if not repo_url:
        return
    try:
        cfg = load_rag_config()
    except Exception:
        cfg = {"collection": os.getenv("RAG_COLLECTION", "rag-poc")}
    coll = collection or cfg.get("collection") or os.getenv("RAG_COLLECTION") or "rag-poc"

    # Normalize branch name from ref if present
    branch = None
    if ref:
        # GitHub push ref looks like 'refs/heads/branch'
        try:
            if ref.startswith("refs/heads/"):
                branch = ref.split("refs/heads/", 1)[1]
            else:
                branch = ref
        except Exception:
            branch = ref
    
    # Query database for last indexed commit (for incremental updates)
    previous_commit = None
    try:
        from mcp.db import SessionLocal
        from mcp.models import IndexedCommit
        db = SessionLocal()
        try:
            last_indexed = db.query(IndexedCommit).filter(
                IndexedCommit.repo_url == repo_url,
                IndexedCommit.branch == (branch or "main"),
                IndexedCommit.collection == coll
            ).order_by(IndexedCommit.indexed_at.desc()).first()
            
            if last_indexed:
                previous_commit = last_indexed.commit_sha
                _logger.info(f"Found previous indexed commit for {repo_url} @ {branch or 'main'}: {previous_commit[:8]}")
        finally:
            db.close()
    except Exception as e:
        _logger.warning(f"Could not query last indexed commit: {e}")

    # Prefer queuing ingestion to Celery (durable, dedupable) when available
    try:
        if task_queue is not None and hasattr(task_queue, "enqueue_ingest"):
            try:
                task_queue.enqueue_ingest(repo_url=repo_url, collection=coll, branch=branch, commit=sha, previous_commit=previous_commit)
                try:
                    INGEST_COUNTER.inc()
                except Exception:
                    pass
                return
            except Exception:
                _logger.exception("Failed to enqueue ingest task for %s; falling back to local spawn", repo_url)
    except Exception:
        _logger.exception("Error while checking task_queue for enqueue_ingest")

    # Fallback: run ingest in a background thread (same behavior as before)
    def _target():
        try:
            cmd = [sys.executable or "python", str(PROJECT_ROOT / "scripts" / "ingest_repo.py"), "--repo-url", repo_url, "--collection", coll]
            if branch:
                cmd.extend(["--branch", branch])
            if sha:
                cmd.extend(["--commit", sha])
            if previous_commit:
                cmd.extend(["--previous-commit", previous_commit])
                _logger.info(f"Incremental update from {previous_commit[:8]} to {sha[:8] if sha else 'HEAD'}")
            _logger.info("Starting background ingest (local): %s", " ".join(cmd))
            env = os.environ.copy()
            proc = subprocess.run(cmd, cwd=str(PROJECT_ROOT), env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            if proc.stdout:
                _logger.info("Ingest stdout: %s", proc.stdout)
            if proc.stderr:
                _logger.warning("Ingest stderr: %s", proc.stderr)
            _logger.info("Ingest finished for %s (rc=%s)", repo_url, proc.returncode)
        except Exception as e:
            _logger.exception("Background ingest failed for %s: %s", repo_url, e)

    try:
        t = threading.Thread(target=_target, daemon=True)
        t.start()
    except Exception:
        _logger.exception("Failed to spawn ingest thread for %s", repo_url)


_check_admin_token = check_admin_token


@app.post("/rag-config")
async def set_rag_config(body: dict, auth: bool = Depends(lambda authorization=None: _check_admin_token(authorization, required_role="editor"))):
    """Set RAG selection config. Example body: {"repo": "https://github.com/owner/repo", "collection": "my-collection"}
    Both keys are optional; missing keys keep previous values.
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    cfg = load_rag_config()
    repos = body.get("repos")
    repo = body.get("repo")
    collection = body.get("collection")
    # support either `repo` (single) or `repos` (list)
    if repos is not None:
        if isinstance(repos, list):
            cfg["repos"] = repos
    elif repo is not None:
        # append single repo if not present
        cfg.setdefault("repos", [])
        if repo not in cfg["repos"]:
            cfg["repos"].append(repo)
    if collection is not None:
        cfg["collection"] = collection
    save_rag_config(cfg)
    return {"status": "ok", "config": cfg}


@app.get("/rag-config")
async def get_rag_config():
    cfg = load_rag_config()
    return {"config": cfg}


# Admin-triggered ingest endpoint: allows agents/operators to force an ingest
# Requires editor/admin role via token and supports incremental updates when
# previous indexed commit is known.
@app.post("/admin/ingest")
async def admin_ingest(body: dict, auth: bool = Depends(lambda authorization=None: _check_admin_token(authorization, required_role="editor"))):
    """Trigger repository ingestion.

    Body example:
    {
      "repo_url": "https://github.com/owner/repo",
      "branch": "main",
      "commit": "optional-commit-sha",
      "collection": "rag-poc",
      "previous_commit": "optional-previous-sha"
    }
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    repo_url = body.get("repo_url")
    branch = body.get("branch")
    commit = body.get("commit")
    collection = body.get("collection")
    previous_commit = body.get("previous_commit")

    if not repo_url:
        raise HTTPException(status_code=400, detail="repo_url is required")

    try:
        _spawn_ingest_for_repo(repo_url=repo_url, collection=collection, ref=(f"refs/heads/{branch}" if branch else None), sha=commit)
        # Note: previous_commit is auto-queried inside _spawn_ingest_for_repo from DB; if provided explicitly
        # and task queue is used, you can extend enqueue_ingest to pass it through.
        return {"status": "started", "repo_url": repo_url, "branch": branch, "commit": commit}
    except Exception as e:
        _logger.exception("Failed to start admin ingest: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to start ingest: {e}")


@app.post("/webhook/github")
async def webhook_github(request: Request):
    """Simple GitHub webhook receiver that enqueues a task for MCP.

    This endpoint normalizes a few common event types into a task dict and
    enqueues it for processing by the MCP via the TaskQueue.
    """
    body = await request.json()
    # Basic normalization
    event = request.headers.get("X-GitHub-Event", "push")
    title = f"GitHub event: {event}"
    description = ""
    files = []
    if event == "push":
        p = body.get("head_commit") or {}
        description = p.get("message", "push event")
        # collect modified files if present
        files = p.get("modified", []) + p.get("added", []) + p.get("removed", [])
    elif event == "issues":
        action = body.get("action")
        issue = body.get("issue", {})
        title = f"Issue {action}: {issue.get('title')}"
        description = issue.get("body", "")

    task = {"title": title, "description": description, "files": files, "source": "github"}
    task_queue.enqueue(task)
    try:
        TASKS_ENQUEUED.inc()
    except Exception:
        pass

    # If this is a push event, try to trigger a background ingestion of the repo
    try:
        if event == "push":
            repo_info = body.get("repository") or {}
            repo_url = repo_info.get("clone_url") or repo_info.get("html_url") or repo_info.get("url")
            ref = body.get("ref")
            sha = body.get("after") or (body.get("head_commit") or {}).get("id")
            # decide whether to ingest based on rag_config
            try:
                cfg = load_rag_config()
                repos_cfg = cfg.get("repos", [])

                def _norm(u: str) -> str:
                    try:
                        if not u:
                            return ""
                        uu = u.lower().strip()
                        if uu.endswith('.git'):
                            uu = uu[:-4]
                        # remove protocol
                        for p in ("https://", "http://", "git@"):
                            if uu.startswith(p):
                                uu = uu[len(p):]
                                break
                        return uu
                    except Exception:
                        return u

                allowed = True
                coll_override = None
                if repos_cfg:
                    # strict mode: only ingest if repo is listed and auto_ingest true
                    allowed = False
                    nurl = _norm(repo_url)
                    for r in repos_cfg:
                        rurl = r.get("url") if isinstance(r, dict) else r
                        if not rurl:
                            continue
                        if _norm(rurl) == nurl or _norm(rurl).endswith(nurl) or nurl.endswith(_norm(rurl)):
                            # match
                            if not r.get("auto_ingest", True):
                                allowed = False
                                break
                            # branch check
                            branches = r.get("branches")
                            if branches:
                                # extract simple branch name from ref
                                branch_name = None
                                if isinstance(ref, str) and ref.startswith("refs/heads/"):
                                    branch_name = ref.split("refs/heads/", 1)[1]
                                elif isinstance(ref, str):
                                    branch_name = ref
                                if branch_name and branch_name not in branches:
                                    allowed = False
                                    break
                            allowed = True
                            coll_override = r.get("collection")
                            break
                if allowed and repo_url:
                    try:
                        _spawn_ingest_for_repo(repo_url, coll_override, ref=ref, sha=sha)
                    except Exception:
                        _logger.exception("Failed to spawn ingest for repo: %s", repo_url)
                else:
                    _logger.info("Webhook ingestion skipped for %s (allowed=%s)", repo_url, allowed)
            except Exception:
                _logger.exception("Error while attempting to trigger ingest from webhook")
    except Exception:
        _logger.exception("Error while processing GitHub webhook")

    return {"status": "enqueued", "task": task}


@app.post("/webhook/jira")
async def webhook_jira(request: Request):
    """Receive JIRA webhooks and enqueue tasks.

    JIRA webhooks send a variety of event types; we normalize basic issue events.
    """
    body = await request.json()
    issue = body.get("issue") or {}
    action = body.get("webhookEvent") or body.get("issue_event_type_name")
    title = f"JIRA event: {action} - {issue.get('key', '')}"
    description = issue.get("fields", {}).get("description", "")
    task = {"title": title, "description": description, "files": [], "source": "jira"}
    task_queue.enqueue(task)
    try:
        TASKS_ENQUEUED.inc()
    except Exception:
        pass
    return {"status": "enqueued", "task": task}


@app.get("/metrics")
async def metrics():
    data, content_type = metrics_response()
    return Response(content=data, media_type=content_type)


@app.get("/events/tasks/{task_id}")
async def task_events(request: Request, task_id: int):
    """Server-sent events endpoint for task updates.

    Clients connect and receive JSON events of shape {type: 'status'|'activity', ...}.
    """
    q: asyncio.Queue = asyncio.Queue()
    _register_task_queue(int(task_id), q)

    # If redis_client is configured use redis pubsub for cross-process events
    if aioredis is not None and redis_client is not None:
        ch = f"task:{task_id}"
        pubsub = redis_client.pubsub()
        await pubsub.subscribe(ch)

        async def redis_generator():
            try:
                yield ': connected\n\n'
                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
                        if message is None:
                            # also check in-memory queue for local events
                            try:
                                ev = q.get_nowait()
                                yield f"data: {json.dumps(ev)}\n\n"
                            except Exception:
                                await asyncio.sleep(0.05)
                            continue
                        data = message.get('data')
                        if isinstance(data, bytes):
                            try:
                                data = data.decode('utf-8')
                            except Exception:
                                data = str(data)
                        yield f"data: {data}\n\n"
                    except asyncio.CancelledError:
                        break
                    except Exception:
                        await asyncio.sleep(0.1)
            finally:
                try:
                    await pubsub.unsubscribe(ch)
                except Exception:
                    pass
                _unregister_task_queue(int(task_id), q)

        return StreamingResponse(redis_generator(), media_type="text/event-stream")

    # Fallback to in-memory queue generator
    async def event_generator():
        try:
            # Send an initial comment to establish connection
            yield ': connected\n\n'
            while True:
                if await request.is_disconnected():
                    break
                try:
                    ev = await q.get()
                except asyncio.CancelledError:
                    break
                try:
                    yield f"data: {json.dumps(ev)}\n\n"
                except Exception:
                    try:
                        yield f"data: {{'type':'error','msg':'serialization error'}}\n\n"
                    except Exception:
                        pass
        finally:
            _unregister_task_queue(int(task_id), q)

    return StreamingResponse(event_generator(), media_type="text/event-stream")





@app.get("/rag-admin")
async def rag_admin(auth: bool = Depends(lambda authorization=None: _check_admin_token(authorization, required_role="admin"))):
    """Simple admin UI to view/add/remove repos for RAG selection."""
    cfg = load_rag_config()
    repos = cfg.get("repos", [])
    collection = cfg.get("collection", "rag-poc")
    repos_html = "".join([f"<li>{r}</li>" for r in repos])

    html = (
        "<!doctype html>"
        "<html>"
        "  <head><meta charset=\"utf-8\"><title>RAG Admin</title></head>"
        "  <body>"
        "    <h4>Admin token:</h4>"
        "    <input type=\"password\" id=\"token\" placeholder=\"Enter admin token\" size=60 />"
        "    <button type=\"button\" onclick=\"saveToken()\">Set Token</button>"
        "    <script>function saveToken(){ window._rag_token = document.getElementById('token').value; }</script>"
        "    <h2>RAG Configuration</h2>"
        "    <p>Collection: <strong>" + str(collection) + "</strong></p>"
        "    <h3>Repos</h3>"
        "    <ul>" + repos_html + "</ul>"
        "    <h3>Add Repository</h3>"
        "    <form id=\"addForm\">"
        "      <input type=\"text\" id=\"repo\" placeholder=\"https://github.com/owner/repo\" size=\"60\" />"
        "      <input type=\"text\" id=\"collection\" placeholder=\"collection (optional)\" />"
        "      <button type=\"button\" onclick=\"addRepo()\">Add</button>"
        "    </form>"
        "    <p id=\"msg\"></p>"
        "    <script>"
        "      async function addRepo(){"
        "        const repo = document.getElementById('repo').value;"
        "        const collection = document.getElementById('collection').value || undefined;"
        "        const body = { 'repo': repo };"
        "        if (collection) body.collection = collection;"
        "        const headers = {'Content-Type':'application/json'};"
        "        if (window._rag_token) headers['Authorization'] = 'Bearer ' + window._rag_token;"
        "        const res = await fetch('/rag-config', {method: 'POST', headers: headers, body: JSON.stringify(body)});"
        "        const data = await res.json();"
        "        document.getElementById('msg').innerText = JSON.stringify(data);"
        "      }"
        "    </script>"
        "  </body>"
        "</html>"
    )
    return html
