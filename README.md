# rag-poc

## Development notes

Quick Dev Ops Notes

1) Celery + Redis (task queue)
- We added optional Celery integration. To enable a durable queue and worker, set `CELERY_BROKER_URL` in `.env` (e.g. `redis://redis:6379/0`) and run `docker compose up redis worker`.

2) Prometheus
- A Prometheus service has been added in `docker-compose.yml` and configuration is in `prometheus/prometheus.yml`. It scrapes MCP at `/metrics`.

3) JIRA ingest
- Use `scripts/jira_connector.py` to fetch issues and `scripts/ingest_jira.py` to ingest them into Qdrant. Configure `JIRA_API_URL`, `JIRA_API_USER`, and `JIRA_API_TOKEN` in your environment.

4) RBAC sample
- A sample `agents/rbac.json` maps example bearer tokens to roles (`admin`, `editor`, `viewer`). For dev, the file is used if `RAG_ROLE_TOKENS` env isn't set.

5) Running agent smoke tests
- Run `python scripts/run_agent_smoke2.py` to execute agents with a mocked CrewAI adapter (no external credentials required).

Quick start (rebuild image, start services)

1) Ensure you have a `.env` file with the following variables (example):

```
OPENAI_API_KEY=sk_...            # optional but recommended for high-quality embeddings
CREWAI_API_KEY=...               # optional if you have CrewAI credentials
CELERY_BROKER_URL=redis://redis:6379/0
QDRANT_URL=http://qdrant:6333
```

2) Build the `mcp` image and bring services up with Docker Compose:

```powershell
docker compose build mcp
docker compose up -d redis qdrant mcp worker prometheus
```

3) Verify MCP is reachable and metrics are exposed:

```powershell
# Health
Invoke-RestMethod -Uri http://localhost:8001/health
# Metrics
Invoke-RestMethod -Uri http://localhost:8001/metrics
```

4) Enqueue a test task:

```powershell
Invoke-RestMethod -Uri http://localhost:8001/run-agents -Method Post -Body (@{ title='smoke'; description='smoke' } | ConvertTo-Json) -ContentType 'application/json'
```

Notes:
- The project includes both an in-memory queue (for local dev) and an optional
	Celery-backed queue for durable/background processing. When `CELERY_BROKER_URL`
	is set and the `worker` service is running, tasks will be dispatched to Celery.
- The `tests/test_crewai_adapter.py` file contains a small pytest that validates
	the adapter fallback behavior. Install `pytest` to run tests locally.
