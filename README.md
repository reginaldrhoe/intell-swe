# rag-poc

Quick Dev Ops Notes

1) Celery + Redis (task queue)
- We added optional Celery integration. To enable a durable queue and worker, set `CELERY_BROKER_URL` in `.env` (e.g. `redis://redis:6379/0`) and run `docker compose up redis worker`.
2) Prometheus
- A Prometheus service has been added in `docker-compose.yml` and configuration is in `prometheus/prometheus.yml`. It scrapes MCP at `/metrics`.

3) JIRA ingest

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

## Release v1.0.0

This repository was tagged `v1.0.0` to capture a stable set of changes that
make the adapter tests and a deterministic ingest smoke test run reliably in
CI without pulling upstream CrewAI transitive pins. Key points:

- In-repo `crewai` shim provides a lightweight CrewAI API surface for tests.
- `setup.py` was added so CI can perform editable installs (`pip install -e .`).
- CI workflows (runner + Docker) run the adapter tests and a deterministic
  ingest smoke test; all tests pass in CI on `main`.

## CI / Deterministic ingest notes

If you want to run CI with a real Qdrant client (end-to-end), the `CI`
workflow accepts a manual `workflow_dispatch` input `qdrant_force_client`.
When set to `1`, the ingest command will construct the low-level Qdrant
client and perform network calls. Example (GitHub Actions UI):

- Open the `Actions` tab, choose the `CI` workflow, click "Run workflow",
  and set `qdrant_force_client` to `1`.

Locally you can run the deterministic ingest smoke test and adapter tests with
the following (PowerShell) commands:

```powershell
# Run unit tests
pytest -q

# Run the deterministic ingest smoke script (no Qdrant network calls by default)
$env:QDRANT_FORCE_CLIENT=0; python scripts/ingest_repo.py --repo . --dry-run

# To exercise real Qdrant (careful: this will perform network writes)
$env:QDRANT_FORCE_CLIENT=1; python scripts/ingest_repo.py --repo .
```

Notes:

- Tests use an autouse pytest fixture to ensure a fresh asyncio event loop per
  test and `asyncio.run(...)` in async tests.
- The adapter uses `asyncio.to_thread(...)` for blocking client calls so the
  event loop is not blocked by sync libraries.

If you'd like, I can also:

- Trigger the `CI` workflow for you with `qdrant_force_client=1` and fetch logs.
- Add a short `RELEASE_NOTES.md` with changelog entries extracted from PRs.

## Local dev: frontend + backend (two-container) example

For a separated frontend container (recommended for dev), a `docker-compose.override.yml`
is provided that will run a minimal `frontend` service on port `3000` and the existing
`mcp` backend on port `8000`.

To try it locally:

```powershell
docker compose build frontend mcp
docker compose up -d
# Frontend: http://localhost:3000
# Backend:  http://localhost:8000
```

Notes:
- The frontend is a placeholder static site (in `web/`) that demonstrates a separate container.
- The backend now exposes a minimal API at `/api` with task and agent CRUD and a tiny DB scaffold (`mcp/db.py`, `mcp/models.py`).

## Frontend demo (docs/index.html)

- A simple static demo copy is included at `docs/index.html` (suitable for publishing via GitHub Pages) and a Vite + React app is scaffolded under `web/` for local development.
- Run the Vite dev server locally from `web/`:

```powershell
cd web
npm install
npm run dev
# open http://localhost:5173
```

- To serve the GitHub Pages demo locally (static):

```powershell
# from repo root
python -m http.server 8003 -d docs
# open http://localhost:8003
```

- The demo accepts a query parameter to configure the backend API base: `?api=http://localhost:8001` (or edit `docs/index.html` DEFAULT_API_BASE).  For auth testing the page and the React app read a bearer token from `localStorage.ragpoc_token` (you can paste a token into the UI Token input).

SSE / Real-time updates
-----------------------

- A Server-Sent Events (SSE) endpoint is available at `GET /events/tasks/{task_id}`. The frontend connects to this endpoint and receives real-time JSON events as agents run. Event shapes include:
  - `{"type":"agent_status","agent":"AgentName","status":"running|done|failed"}`
  - `{"type":"activity","agent":"AgentName","content":"...","created_at":"..."}`
  - `{"type":"status","status":"running|done|failed"}`

- Local development: the backend uses an in-memory SSE pub/sub by default so the frontend must connect to the same backend process/container that executes the run.

- Cross-container / scaled deployments: to support SSE across multiple backend instances, set `REDIS_URL` (or `CELERY_BROKER_URL`) to a Redis URL (e.g. `redis://redis:6379/0`) and ensure a Redis service is running. When Redis is configured the backend will publish events to Redis channels (`task:{id}`) and any backend instance with an SSE client can subscribe and stream events to connected browsers.

  Example environment variable for docker-compose `.env` or service env:

  ```env
  REDIS_URL=redis://redis:6379/0
  # or
  CELERY_BROKER_URL=redis://redis:6379/0
  ```

- Notes:
  - SSE connections require the browser to be able to reach the backend (`CORS_ALLOW_ORIGINS` includes `http://localhost:5173` by default).
  - The SSE implementation falls back to an in-process queue when Redis is not available; for production use with multiple replicas, configure Redis as shown above.

OAuth SSO (GitHub / GitLab)
---------------------------------
The backend includes a minimal OAuth implementation for GitHub and GitLab. Set the following
environment variables in your development environment (or `.env`) before running the app:

- `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` (for GitHub OAuth)
- `GITLAB_CLIENT_ID` and `GITLAB_CLIENT_SECRET` (for GitLab OAuth)
- `OAUTH_REDIRECT_BASE` (e.g. `http://localhost:8000`)
- `OAUTH_FRONTEND_CALLBACK` (the frontend URL to redirect to after login, default: `http://localhost:3000/`)
- `OAUTH_JWT_SECRET` (secret used to sign issued JWTs)

Endpoints:

- `GET /auth/login?provider=github|gitlab` — start OAuth flow
- `GET /auth/callback?provider=...&code=...&state=...` — OAuth callback (exchanges code, creates local user, redirects to frontend with `#access_token=...`)
- `GET /auth/me` — debug endpoint to decode the JWT (provide `Authorization: Bearer <token>`)

For local testing you can register an OAuth app on GitHub with callback URL set to
`http://localhost:8000/auth/callback?provider=github` and then run the login URL in your browser.

Next step: run the services and I can scaffold a real React or Next.js app into `web/` and wire the frontend login button to `/auth/login`.

### Generating `RELEASE_NOTES.md`

A small helper script has been added at `scripts/generate_release_notes.py` to
produce a simple `RELEASE_NOTES.md` from your git history. It finds the latest
tag (or uses `--tag`) and lists commits between the previous tag and the
selected tag.

Run it like this (PowerShell):

```powershell
python scripts/generate_release_notes.py
# or specify tag/output
python scripts/generate_release_notes.py --tag v1.0.0 -o RELEASE_NOTES.md
```

The script expects to be run from the repository root and requires `git` to be
available on your PATH. After generation, review `RELEASE_NOTES.md` and edit
as needed before publishing a release.
