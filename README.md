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
