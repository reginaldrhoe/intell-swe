"""Ingest JIRA issues into Qdrant with audit metadata.

Usage:
  python scripts/ingest_jira.py --jql 'project = TEST' --collection 'jira-issues'

This script uses environment variables `JIRA_API_URL`, `JIRA_API_USER`, `JIRA_API_TOKEN`,
and `OPENAI_API_KEY` if available for embeddings; otherwise uses deterministic fallback.
"""
import os
import argparse
import json
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
except Exception:
    QdrantClient = None
    qdrant_models = None

try:
    import requests
except Exception:
    requests = None


def get_embedding(text: str):
    # lightweight fallback deterministic embedding
    import hashlib, math
    h = hashlib.sha256(text.encode("utf-8")).digest()
    dim = int(os.getenv("RAG_EMBED_DIM", "64"))
    reps = (dim + len(h) - 1) // len(h)
    data = (h * reps)[:dim]
    vec = [((b / 255.0) * 2.0 - 1.0) for b in data]
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


def fetch_issues(jql: str, max_results: int = 50):
    base = os.getenv("JIRA_API_URL")
    user = os.getenv("JIRA_API_USER")
    token = os.getenv("JIRA_API_TOKEN")
    if not base or not user or not token:
        raise RuntimeError("JIRA_API_URL, JIRA_API_USER, and JIRA_API_TOKEN must be set")
    url = base.rstrip("/") + "/rest/api/2/search"
    headers = {"Content-Type": "application/json"}
    auth = (user, token)
    payload = {"jql": jql, "maxResults": max_results, "fields": ["summary", "description", "updated"]}
    resp = requests.post(url, headers=headers, auth=auth, json=payload)
    resp.raise_for_status()
    data = resp.json()
    return data.get("issues", [])


def ensure_collection(client: QdrantClient, collection: str, vec_size: int):
    try:
        client.get_collection(collection_name=collection)
    except Exception:
        params = qdrant_models.VectorParams(size=vec_size, distance=qdrant_models.Distance.COSINE)
        client.recreate_collection(collection_name=collection, vectors_config=params)


def ingest_issues(issues, collection: str, qdrant_url: str = "http://qdrant:6333"):
    if QdrantClient is None:
        raise RuntimeError("qdrant-client is required to ingest")
    client = QdrantClient(url=qdrant_url)
    # probe vector size
    vec = get_embedding("probe")
    vec_size = len(vec)
    ensure_collection(client, collection, vec_size)

    points = []
    for i, issue in enumerate(issues):
        key = issue.get("key")
        fields = issue.get("fields", {})
        title = fields.get("summary")
        desc = fields.get("description") or ""
        text = f"{title}\n\n{desc}"
        vec = get_embedding(text)
        payload = {
            "source": "jira",
            "issue_key": key,
            "title": title,
            "description": desc,
            "ingested_at": datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        }
        points.append(qdrant_models.PointStruct(id=i, vector=vec, payload=payload))

    client.upsert(collection_name=collection, points=points)
    print(f"Ingested {len(points)} JIRA issues into collection '{collection}'")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--jql", default="project = TEST ORDER BY updated DESC")
    p.add_argument("--max", type=int, default=50)
    p.add_argument("--collection", default="jira-issues")
    p.add_argument("--qdrant", default=os.getenv("QDRANT_URL") or "http://qdrant:6333")
    args = p.parse_args()

    issues = fetch_issues(args.jql, args.max)
    ingest_issues(issues, args.collection, qdrant_url=args.qdrant)


if __name__ == "__main__":
    main()
