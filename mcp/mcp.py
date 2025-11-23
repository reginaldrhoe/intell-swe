from fastapi import FastAPI, HTTPException, Depends, Header, Request, Response
import os
import json
from typing import Dict, Any
from pathlib import Path
from agents.agents import MasterControlPanel
from agents.task_queue import TaskQueue
from agents.scheduler import SimpleScheduler
from mcp.auth import check_admin_token
from mcp.metrics import TASKS_ENQUEUED, AGENT_RUNS, INGEST_COUNTER, metrics_response

app = FastAPI()

# Instantiate the MasterControlPanel (or inject a different implementation)
mcp = MasterControlPanel()

# Task queue used by webhook endpoints
task_queue = TaskQueue()

# Simple scheduler for periodic jobs
scheduler = SimpleScheduler()


@app.on_event("startup")
async def _startup():
    # start the task queue worker; worker delegates to mcp.handle_task
    def _worker_callable(task):
        # Wrap the async call to mcp.handle_task
        return mcp.handle_task(task)

    task_queue.start(_worker_callable)

    # Example scheduled job: daily summary (runs every 24h)
    async def _daily_summary():
        # placeholder: in future generate a summary report
        return

    scheduler.add_job(_daily_summary, interval_seconds=24 * 3600)


@app.on_event("shutdown")
async def _shutdown():
    try:
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


def deterministic_embedding(text: str, dim: int = 64):
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

    # 3) Deterministic fallback
    return deterministic_embedding(text)


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
    try:
        # Call the async handler directly to avoid blocking the event loop
        results = await mcp.handle_task(task)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
            return json.load(fh)
    except Exception:
        return {"repo": None, "collection": "rag-poc"}


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
