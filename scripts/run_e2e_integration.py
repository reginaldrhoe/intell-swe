"""End-to-end integration scaffold.

This script exercises ingestion -> vector indexing -> retrieval -> visibility.

It supports a deterministic `--mock` mode for CI or local runs without an OpenAI key.
In `--mock` mode, we avoid calling any LLM-dependent agent endpoint and instead
assert retrieval via the app's `/similarity-search` API after triggering ingestion
through the GitHub webhook endpoint.
"""
import os
import time
import json
import argparse
import requests


MCP = os.environ.get('MCP_URL', 'http://localhost:8001')
AUTH = {'Authorization': 'Bearer demo'}

from typing import Optional


def trigger_ingest_via_webhook(repo_url: str, ref: Optional[str] = None, sha: Optional[str] = None):
    url = f"{MCP}/webhook/github"
    payload = {
        'repository': {'clone_url': repo_url, 'html_url': repo_url},
        'head_commit': {'message': 'e2e mock ingest trigger', 'modified': [], 'added': [], 'removed': [], 'id': sha or 'e2esha'},
        'ref': ref or 'refs/heads/main',
        'after': sha or 'e2esha'
    }
    headers = dict(AUTH)
    headers['X-GitHub-Event'] = 'push'
    print('Triggering ingest via webhook...')
    r = requests.post(url, json=payload, headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()


def poll_similarity(query: str, collection: Optional[str] = None, timeout: int = 120, interval: float = 2.0):
    url = f"{MCP}/similarity-search"
    start = time.time()
    while True:
        body = {'query': query}
        if collection:
            body['collection'] = collection
        try:
            resp = requests.post(url, json=body, headers=AUTH, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                results = data.get('results') or []
                if results:
                    return data
        except Exception:
            pass
        if time.time() - start > timeout:
            raise SystemExit(f"Timed out waiting for similarity results for query '{query}'")
        time.sleep(interval)


def call_agent(task_id, query, timeout=30):
    url = f"{MCP}/run-agents"
    payload = {'id': task_id, 'query': query}
    print('Calling agent...')
    r = requests.post(url, json=payload, headers=AUTH, timeout=timeout)
    r.raise_for_status()
    return r.json()


def mocked_agent_response(task_id, query, ingested_text):
    # Return deterministic, minimal agent-like payload containing the ingested text
    return {
        'task_id': task_id,
        'query': query,
        'results': {'mock_agent': f"Retrieved snippet: {ingested_text[:200]}"}
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--mock', action='store_true', help='Run in deterministic mock mode (no OpenAI calls)')
    ap.add_argument('--repo-url', default=os.environ.get('E2E_REPO_URL', 'https://github.com/reginaldrhoe/rag-poc.git'))
    ap.add_argument('--query', default='RUN_AGENTS_DBG', help='Query text expected to appear in indexed code')
    args = ap.parse_args(argv)

    mock_mode = args.mock or (os.environ.get('OPENAI_API_KEY') is None)
    if mock_mode:
        print('E2E: Running in MOCK mode (no external OpenAI calls)')
    else:
        print('E2E: Running in LIVE mode (OpenAI will be used if invoked by the app)')

    # Create a task first (used by agent call in live mode; harmless in mock mode)
    print('Creating task...')
    resp = requests.post(f"{MCP}/api/tasks", json={'title':'e2e-test','description':'created by e2e script'}, headers=AUTH)
    resp.raise_for_status()
    data = resp.json()
    task_id = data.get('id') or data.get('task', {}).get('id') or data.get('data', {}).get('id')
    if not task_id:
        raise SystemExit('Could not create task')
    print('Task id:', task_id)

    # Trigger ingest via webhook for the configured repo
    trigger_ingest_via_webhook(args.repo_url)

    if mock_mode:
        # In mock mode, assert retrieval via similarity-search (no LLM calls)
        print('Polling similarity-search for query:', args.query)
        sim = poll_similarity(args.query)
        print('Similarity results:', json.dumps(sim)[:1000])
        results = sim.get('results') or []
        ok = bool(results)
        if ok:
            print('E2E: PASS — retrieval content visible via similarity-search')
            return 0
        else:
            print('E2E: FAIL — no similarity results found')
            return 2
    else:
        # Call the real agent endpoint; success criteria depends on downstream visibility
        result = call_agent(task_id, args.query)
        print('Agent result:', json.dumps(result)[:1000])
        combined = json.dumps(result)
        if args.query.lower() in combined.lower():
            print('E2E: PASS — retrieval content visible in agent result')
            return 0
        else:
            print('E2E: FAIL — expected retrieval text not present in agent result')
            return 2


if __name__ == '__main__':
    exit(main())
