# Test Coverage Report — E2E and Smoke vs. System Components

Date: 2025-11-29

## Scope
This report maps the currently implemented end-to-end (E2E) and smoke tests to core system components, highlights coverage gaps, and proposes targeted next tests. It focuses on practical scenario coverage rather than line/branch metrics.

## Current Tests and What They Cover

- `tests/test_mcp_end_to_end.py`
  - Covers the FastAPI app happy-path: creating/running an agent flow end-to-end within the MCP service.
- `tests/test_lock_distributed.py` and `scripts/run_lock_smoke.*`
  - Covers duplicate-run protection and distributed lock behavior around `POST /run-agents`.
- `tests/test_ingest.py`, `tests/test_ingest_deterministic.py`
  - Covers repository ingestion pipeline basics and deterministic embedding behavior.
- `test_incremental_sync.py`
  - Covers git-diff–based incremental sync: added/modified/deleted detection, Qdrant deletion by `file_path`, and `IndexedCommit` persistence.
- `tests/test_agents.py`
  - Covers CrewAI agent orchestration basics.
- `tests/test_crewai_adapter.py`
  - Covers the OpenAI adapter (ensures real chat completions path vs. stub/mock behavior).
- `scripts/run_agent_smoke2.py`, `scripts/run_crewai_smoke.py`
  - Manual smoke paths for agent responses and adapter functionality.
- `scripts/run_e2e_integration.py` (mock/live)
  - E2E scenario: task creation → ingestion → agent invocation → retrieval check; supports mock OpenAI.
- `tests/ui/test_ui_agent_flow.py`
  - Optional UI smoke: minimal Playwright flow to assert visible response from a query.
- CI workflow `\.github/workflows/ci_ingest_smoke.yml`
  - Qdrant service smoke: create collection → upsert deterministic vector → search.

## Component Coverage Map

| Component | Key Endpoints / Functions | Covered By | Status |
|---|---|---|---|
| Agent run orchestration | `POST /run-agents`, SSE events | E2E test, lock tests | Covered (happy-path + duplicate protection) |
| Health & Metrics | `GET /health`, `GET /metrics` | — | Gap |
| Similarity Search API | `POST /similarity-search` | — | Gap |
| RAG Config API | `POST /rag-config`, `GET /rag-config` | — | Gap |
| Admin Ingest | `POST /admin/ingest` | Incremental sync covered at script level; endpoint not directly | Partial (gap at API layer) |
| GitHub Webhook | `POST /webhook/github` | — | Gap |
| JIRA Webhook | `POST /webhook/jira` | — | Gap |
| Task Events (SSE) | `GET /events/tasks/{task_id}` | E2E (implicitly via run) | Partial |
| RAG Admin View | `GET /rag-admin` | — | Gap |
| Ingestion Pipeline | `scripts/ingest_repo.py` | Ingest unit tests + incremental sync E2E | Covered |
| Qdrant Integration | Upsert/delete, filters by metadata | Incremental sync test, CI smoke | Covered (key paths) |
| DB Models | `IndexedCommit` | Incremental sync test (persistence) | Partial (no unit tests) |
| OpenAI Adapter | `agents/crewai_adapter.py` | Unit test + smokes | Covered |
| Agents (CrewAI) | Orchestration, prompts | Unit test + smokes | Covered (basics) |
| Frontend UI | Query → response path | Playwright smoke (optional) | Partial |

## Gaps and Targeted Next Tests

1) Health & Metrics
   - Tests: `GET /health` returns 200; `GET /metrics` exposes Prometheus counters.
   - Value: Catch regressions in observability endpoints used by ops/monitoring.

2) Similarity Search API
   - Tests: `POST /similarity-search` with seeded Qdrant returns expected payload ordering.
   - Value: Validates public-facing semantic search behavior independent of agent runs.

3) RAG Config API (POST/GET)
   - Tests: Create/update config, then GET returns saved config; invalid payloads rejected.
   - Value: Ensures operator workflows via Settings UI remain consistent.

4) Admin Ingest Endpoint
   - Tests: `POST /admin/ingest` with (a) full ingest, (b) incremental ingest (`previous_commit`) executes and logs expected messages; RBAC token enforced.
   - Value: Validates manual recovery path relied upon by ops.

5) Webhooks (GitHub/JIRA)
   - Tests: Minimal normalized payloads trigger ingest (GitHub) and are accepted (JIRA); invalid signatures/payloads are rejected.
   - Value: Protects automation entry points; reduces CI/CD drift.

6) SSE Events Endpoint
   - Tests: Connect to `GET /events/tasks/{id}` and assert receipt of minimal event stream after `POST /run-agents`.
   - Value: Guarantees live updates to UI/workers.

7) DB Model Unit Tests
   - Tests: Direct unit tests for `IndexedCommit` lifecycle and query helpers independent of ingestion.
   - Value: Speeds debugging of schema/ORM changes.

8) Frontend UI Smoke (stabilize)
   - Tests: Parameterize selectors and host; assert minimal response content with mock OpenAI.
   - Value: Early warning on UI regression without requiring full E2E.

## Suggested Test Skeletons (concise)

```python
# tests/test_health_metrics.py
def test_health(client):
    r = client.get('/health'); assert r.status_code == 200

def test_metrics(client):
    r = client.get('/metrics'); assert r.status_code == 200; assert 'process_cpu_seconds_total' in r.text

# tests/test_similarity_search_api.py
def test_similarity_search_seeded(client, seeded_qdrant):
    r = client.post('/similarity-search', json={'text':'hello','k':1})
    assert r.status_code == 200; assert r.json()['results']

# tests/test_rag_config_api.py
def test_rag_config_roundtrip(client):
    cfg = {"collection":"rag-poc","repos":[{"url":"https://x/y.git","branches":["main"]}]}
    assert client.post('/rag-config', json=cfg).status_code == 200
    got = client.get('/rag-config').json(); assert got['collection'] == 'rag-poc'

# tests/test_admin_ingest_api.py
def test_admin_ingest_full(client, admin_token):
    r = client.post('/admin/ingest', headers={'Authorization': f'Bearer {admin_token}'}, json={"repo_url":"https://x/y.git","branch":"main"})
    assert r.status_code in (200,202)

# tests/test_webhooks.py
def test_github_push_webhook_triggers_ingest(client, gh_event):
    r = client.post('/webhook/github', headers=gh_event.headers, json=gh_event.payload)
    assert r.status_code in (200,202)
```

> Note: Fixtures like `client`, `seeded_qdrant`, `admin_token`, and `gh_event` can extend `tests/conftest.py`.

## How to Run

```powershell
# Unit and integration tests
pytest -q

# E2E integration (mock)
python scripts/run_e2e_integration.py --mock

# Agent smoke tests
python scripts/run_agent_smoke2.py
python scripts/run_crewai_smoke.py

# Lock smoke (PowerShell)
.\u005cscripts\run_lock_smoke.ps1 -TaskId 11
```

## Optional Coverage Metrics
If desired, add `pytest-cov` and run with coverage:

```powershell
python -m pip install pytest-cov
pytest --cov=mcp --cov=agents --cov=scripts --cov-report=term-missing -q
```

## Summary
- E2E and smoke coverage is strong for: agent runs, ingestion (incl. incremental), OpenAI adapter, and Qdrant integration.
- Primary gaps: health/metrics endpoints, Similarity Search API, RAG config API, admin ingest API at the endpoint layer, webhooks, SSE events, and focused DB unit tests.
- The proposed next tests close operational and API-surface gaps with minimal scaffolding.

Highlights:

Covered: agent run flow (/run-agents), lock duplicate protection, ingestion (incl. incremental sync + Qdrant deletes), OpenAI adapter, Qdrant integration. Optional UI smoke included.
Gaps: /health and /metrics, /similarity-search, RAG config (POST/GET), /admin/ingest at the endpoint layer (pipeline covered), /webhook/github and /webhook/jira, SSE events endpoint, DB unit tests for IndexedCommit.
Next tests: compact skeletons provided for each missing area with suggested fixtures.
Quick runs:

Unit/integration: pytest -q
E2E mock: python run_e2e_integration.py --mock
Smokes: python scripts/run_agent_smoke2.py; python run_crewai_smoke.py
Lock smoke (PowerShell): run_lock_smoke.ps1 -TaskId 11