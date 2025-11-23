from fastapi import FastAPI, HTTPException
import os
import json
from typing import Dict, Any
from pathlib import Path
from agents.agents import MasterControlPanel

app = FastAPI()

# Instantiate the MasterControlPanel (or inject a different implementation)
mcp = MasterControlPanel()

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
    if OpenAIEmbeddings is not None:
        try:
            emb = OpenAIEmbeddings()  # type: ignore
            try:
                return emb.embed_documents([text])[0]
            except Exception:
                return emb.embed_query(text)
        except Exception:
            return deterministic_embedding(text)
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
            return {"repo": None, "collection": "rag-poc"}
        with open(RAG_CONFIG_PATH, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {"repo": None, "collection": "rag-poc"}


def save_rag_config(cfg: Dict[str, Any]):
    try:
        RAG_CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(RAG_CONFIG_PATH, "w", encoding="utf-8") as fh:
            json.dump(cfg, fh, indent=2)
    except Exception as e:
        raise


@app.post("/rag-config")
async def set_rag_config(body: dict):
    """Set RAG selection config. Example body: {"repo": "https://github.com/owner/repo", "collection": "my-collection"}
    Both keys are optional; missing keys keep previous values.
    """
    if not isinstance(body, dict):
        raise HTTPException(status_code=400, detail="Request body must be a JSON object")

    cfg = load_rag_config()
    repo = body.get("repo")
    collection = body.get("collection")
    if repo is not None:
        cfg["repo"] = repo
    if collection is not None:
        cfg["collection"] = collection
    save_rag_config(cfg)
    return {"status": "ok", "config": cfg}


@app.get("/rag-config")
async def get_rag_config():
    cfg = load_rag_config()
    return {"config": cfg}
